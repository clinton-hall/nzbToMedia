# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os.path
import re
import sqlite3
import sys
import time

from six import text_type, PY2

import core
from core import logger
from core import permissions

if PY2:
    class Row(sqlite3.Row, object):
        """
        Row factory that uses Byte Strings for keys.

        The sqlite3.Row in Python 2 does not support unicode keys.
        This overrides __getitem__ to attempt to encode the key to bytes first.
        """

        def __getitem__(self, item):
            """
            Get an item from the row by index or key.

            :param item: Index or Key of item to return.
            :return: An item from the sqlite3.Row.
            """
            try:
                # sqlite3.Row column names should be Bytes in Python 2
                item = item.encode()
            except AttributeError:
                pass  # assume item is a numeric index

            return super(Row, self).__getitem__(item)
else:
    from sqlite3 import Row


def db_filename(filename='nzbtomedia.db', suffix=None):
    """
    Return the correct location of the database file.

    @param filename: The sqlite database filename to use. If not specified,
                     will be made to be nzbtomedia.db
    @param suffix: The suffix to append to the filename. A '.' will be added
                   automatically, i.e. suffix='v0' will make dbfile.db.v0
    @return: the correct location of the database file.
    """
    if suffix:
        filename = '{0}.{1}'.format(filename, suffix)
    return core.os.path.join(core.APP_ROOT, filename)


class DBConnection(object):
    def __init__(self, filename='nzbtomedia.db', suffix=None, row_type=None):
        self.filename = filename
        path = db_filename(filename)
        try:
            self.connection = sqlite3.connect(path, 20)
        except sqlite3.OperationalError as error:
            if os.path.exists(path):
                logger.error('Please check permissions on database: {0}'.format(path))
            else:
                logger.error('Database file does not exist')
                logger.error('Please check permissions on directory: {0}'.format(path))
                path = os.path.dirname(path)
            mode = permissions.mode(path)
            owner, group = permissions.ownership(path)
            logger.error(
                "=== PERMISSIONS ===========================\n"
                "  Path : {0}\n"
                "  Mode : {1}\n"
                "  Owner: {2}\n"
                "  Group: {3}\n"
                "===========================================".format(path, mode, owner, group),
            )
        else:
            self.connection.row_factory = Row

    def check_db_version(self):
        result = None
        try:
            result = self.select('SELECT db_version FROM db_version')
        except sqlite3.OperationalError as e:
            if 'no such table: db_version' in e.args[0]:
                return 0

        if result:
            return int(result[0]['db_version'])
        else:
            return 0

    def fetch(self, query, args=None):
        if query is None:
            return

        sql_result = None
        attempt = 0

        while attempt < 5:
            try:
                if args is None:
                    logger.log('{name}: {query}'.format(name=self.filename, query=query), logger.DB)
                    cursor = self.connection.cursor()
                    cursor.execute(query)
                    sql_result = cursor.fetchone()[0]
                else:
                    logger.log('{name}: {query} with args {args}'.format
                               (name=self.filename, query=query, args=args), logger.DB)
                    cursor = self.connection.cursor()
                    cursor.execute(query, args)
                    sql_result = cursor.fetchone()[0]

                # get out of the connection attempt loop since we were successful
                break
            except sqlite3.OperationalError as error:
                if 'unable to open database file' in error.args[0] or 'database is locked' in error.args[0]:
                    logger.log(u'DB error: {msg}'.format(msg=error), logger.WARNING)
                    attempt += 1
                    time.sleep(1)
                else:
                    logger.log(u'DB error: {msg}'.format(msg=error), logger.ERROR)
                    raise
            except sqlite3.DatabaseError as error:
                logger.log(u'Fatal error executing query: {msg}'.format(msg=error), logger.ERROR)
                raise

        return sql_result

    def mass_action(self, querylist, log_transaction=False):
        if querylist is None:
            return

        sql_result = []
        attempt = 0

        while attempt < 5:
            try:
                for qu in querylist:
                    if len(qu) == 1:
                        if log_transaction:
                            logger.log(qu[0], logger.DEBUG)
                        sql_result.append(self.connection.execute(qu[0]))
                    elif len(qu) > 1:
                        if log_transaction:
                            logger.log(u'{query} with args {args}'.format(query=qu[0], args=qu[1]), logger.DEBUG)
                        sql_result.append(self.connection.execute(qu[0], qu[1]))
                self.connection.commit()
                logger.log(u'Transaction with {x} query\'s executed'.format(x=len(querylist)), logger.DEBUG)
                return sql_result
            except sqlite3.OperationalError as error:
                sql_result = []
                if self.connection:
                    self.connection.rollback()
                if 'unable to open database file' in error.args[0] or 'database is locked' in error.args[0]:
                    logger.log(u'DB error: {msg}'.format(msg=error), logger.WARNING)
                    attempt += 1
                    time.sleep(1)
                else:
                    logger.log(u'DB error: {msg}'.format(msg=error), logger.ERROR)
                    raise
            except sqlite3.DatabaseError as error:
                if self.connection:
                    self.connection.rollback()
                logger.log(u'Fatal error executing query: {msg}'.format(msg=error), logger.ERROR)
                raise

        return sql_result

    def action(self, query, args=None):
        if query is None:
            return

        sql_result = None
        attempt = 0

        while attempt < 5:
            try:
                if args is None:
                    logger.log(u'{name}: {query}'.format(name=self.filename, query=query), logger.DB)
                    sql_result = self.connection.execute(query)
                else:
                    logger.log(u'{name}: {query} with args {args}'.format
                               (name=self.filename, query=query, args=args), logger.DB)
                    sql_result = self.connection.execute(query, args)
                self.connection.commit()
                # get out of the connection attempt loop since we were successful
                break
            except sqlite3.OperationalError as error:
                if 'unable to open database file' in error.args[0] or 'database is locked' in error.args[0]:
                    logger.log(u'DB error: {msg}'.format(msg=error), logger.WARNING)
                    attempt += 1
                    time.sleep(1)
                else:
                    logger.log(u'DB error: {msg}'.format(msg=error), logger.ERROR)
                    raise
            except sqlite3.DatabaseError as error:
                logger.log(u'Fatal error executing query: {msg}'.format(msg=error), logger.ERROR)
                raise

        return sql_result

    def select(self, query, args=None):

        sql_results = self.action(query, args).fetchall()

        if sql_results is None:
            return []

        return sql_results

    def upsert(self, table_name, value_dict, key_dict):

        def gen_params(my_dict):
            return [
                '{key} = ?'.format(key=k)
                for k in my_dict.keys()
            ]

        changes_before = self.connection.total_changes
        items = list(value_dict.values()) + list(key_dict.values())
        self.action(
            'UPDATE {table} '
            'SET {params} '
            'WHERE {conditions}'.format(
                table=table_name,
                params=', '.join(gen_params(value_dict)),
                conditions=' AND '.join(gen_params(key_dict)),
            ),
            items,
        )

        if self.connection.total_changes == changes_before:
            self.action(
                'INSERT OR IGNORE INTO {table} ({columns}) '
                'VALUES ({values})'.format(
                    table=table_name,
                    columns=', '.join(map(text_type, value_dict.keys())),
                    values=', '.join(['?'] * len(value_dict.values())),
                ),
                list(value_dict.values()),
            )

    def table_info(self, table_name):
        # FIXME ? binding is not supported here, but I cannot find a way to escape a string manually
        cursor = self.connection.execute('PRAGMA table_info({0})'.format(table_name))
        return {
            column['name']: {'type': column['type']}
            for column in cursor
        }


def sanity_check_database(connection, sanity_check):
    sanity_check(connection).check()


class DBSanityCheck(object):
    def __init__(self, connection):
        self.connection = connection

    def check(self):
        pass


# ===============
# = Upgrade API =
# ===============

def upgrade_database(connection, schema):
    logger.log(u'Checking database structure...', logger.MESSAGE)
    try:
        _process_upgrade(connection, schema)
    except Exception as error:
        logger.error(error)
        sys.exit(1)


def pretty_name(class_name):
    return ' '.join([x.group() for x in re.finditer('([A-Z])([a-z0-9]+)', class_name)])


def _process_upgrade(connection, upgrade_class):
    instance = upgrade_class(connection)
    logger.log(u'Checking {name} database upgrade'.format
               (name=pretty_name(upgrade_class.__name__)), logger.DEBUG)
    if not instance.test():
        logger.log(u'Database upgrade required: {name}'.format
                   (name=pretty_name(upgrade_class.__name__)), logger.MESSAGE)
        try:
            instance.execute()
        except sqlite3.DatabaseError as error:
            print(u'Error in {name}: {msg}'.format
                  (name=upgrade_class.__name__, msg=error))
            raise
        logger.log(u'{name} upgrade completed'.format
                   (name=upgrade_class.__name__), logger.DEBUG)
    else:
        logger.log(u'{name} upgrade not required'.format
                   (name=upgrade_class.__name__), logger.DEBUG)

    for upgradeSubClass in upgrade_class.__subclasses__():
        _process_upgrade(connection, upgradeSubClass)


# Base migration class. All future DB changes should be subclassed from this class
class SchemaUpgrade(object):
    def __init__(self, connection):
        self.connection = connection

    def has_table(self, table_name):
        return len(self.connection.action('SELECT 1 FROM sqlite_master WHERE name = ?;', (table_name,)).fetchall()) > 0

    def has_column(self, table_name, column):
        return column in self.connection.table_info(table_name)

    def add_column(self, table, column, data_type='NUMERIC', default=0):
        self.connection.action('ALTER TABLE {0} ADD {1} {2}'.format(table, column, data_type))
        self.connection.action('UPDATE {0} SET {1} = ?'.format(table, column), (default,))

    def check_db_version(self):
        result = self.connection.select('SELECT db_version FROM db_version')
        if result:
            return int(result[-1]['db_version'])
        else:
            return 0

    def inc_db_version(self):
        new_version = self.check_db_version() + 1
        self.connection.action('UPDATE db_version SET db_version = ?', [new_version])
        return new_version
