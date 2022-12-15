from __future__ import annotations

import re
import sqlite3
import time

import nzb2media
from nzb2media import logger


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
        filename = f'{filename}.{suffix}'
    return nzb2media.os.path.join(nzb2media.APP_ROOT, filename)


class DBConnection:
    def __init__(self, filename='nzbtomedia.db', suffix=None, row_type=None):

        self.filename = filename
        self.connection = sqlite3.connect(db_filename(filename), 20)
        self.connection.row_factory = sqlite3.Row

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
                    logger.log(f'{self.filename}: {query}', logger.DB)
                    cursor = self.connection.cursor()
                    cursor.execute(query)
                    sql_result = cursor.fetchone()[0]
                else:
                    logger.log(
                        f'{self.filename}: {query} with args {args}',
                        logger.DB,
                    )
                    cursor = self.connection.cursor()
                    cursor.execute(query, args)
                    sql_result = cursor.fetchone()[0]

                # get out of the connection attempt loop since we were successful
                break
            except sqlite3.OperationalError as error:
                if (
                    'unable to open database file' in error.args[0]
                    or 'database is locked' in error.args[0]
                ):
                    logger.log(f'DB error: {error}', logger.WARNING)
                    attempt += 1
                    time.sleep(1)
                else:
                    logger.log(f'DB error: {error}', logger.ERROR)
                    raise
            except sqlite3.DatabaseError as error:
                logger.log(
                    f'Fatal error executing query: {error}', logger.ERROR,
                )
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
                            logger.log(
                                f'{qu[0]} with args {qu[1]}', logger.DEBUG,
                            )
                        sql_result.append(
                            self.connection.execute(qu[0], qu[1]),
                        )
                self.connection.commit()
                logger.log(
                    f'Transaction with {len(querylist)} query\'s executed',
                    logger.DEBUG,
                )
                return sql_result
            except sqlite3.OperationalError as error:
                sql_result = []
                if self.connection:
                    self.connection.rollback()
                if (
                    'unable to open database file' in error.args[0]
                    or 'database is locked' in error.args[0]
                ):
                    logger.log(f'DB error: {error}', logger.WARNING)
                    attempt += 1
                    time.sleep(1)
                else:
                    logger.log(f'DB error: {error}', logger.ERROR)
                    raise
            except sqlite3.DatabaseError as error:
                if self.connection:
                    self.connection.rollback()
                logger.log(
                    f'Fatal error executing query: {error}', logger.ERROR,
                )
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
                    logger.log(f'{self.filename}: {query}', logger.DB)
                    sql_result = self.connection.execute(query)
                else:
                    logger.log(
                        f'{self.filename}: {query} with args {args}',
                        logger.DB,
                    )
                    sql_result = self.connection.execute(query, args)
                self.connection.commit()
                # get out of the connection attempt loop since we were successful
                break
            except sqlite3.OperationalError as error:
                if (
                    'unable to open database file' in error.args[0]
                    or 'database is locked' in error.args[0]
                ):
                    logger.log(f'DB error: {error}', logger.WARNING)
                    attempt += 1
                    time.sleep(1)
                else:
                    logger.log(f'DB error: {error}', logger.ERROR)
                    raise
            except sqlite3.DatabaseError as error:
                logger.log(
                    f'Fatal error executing query: {error}', logger.ERROR,
                )
                raise

        return sql_result

    def select(self, query, args=None):

        sql_results = self.action(query, args).fetchall()

        if sql_results is None:
            return []

        return sql_results

    def upsert(self, table_name, value_dict, key_dict):
        def gen_params(my_dict):
            return [f'{k} = ?' for k in my_dict.keys()]

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
                    columns=', '.join(map(str, value_dict.keys())),
                    values=', '.join(['?'] * len(value_dict.values())),
                ),
                list(value_dict.values()),
            )

    def table_info(self, table_name):
        # FIXME ? binding is not supported here, but I cannot find a way to escape a string manually
        cursor = self.connection.execute(f'PRAGMA table_info({table_name})')
        return {column['name']: {'type': column['type']} for column in cursor}


def sanity_check_database(connection, sanity_check):
    sanity_check(connection).check()


class DBSanityCheck:
    def __init__(self, connection):
        self.connection = connection

    def check(self):
        pass


# ===============
# = Upgrade API =
# ===============


def upgrade_database(connection, schema):
    logger.log('Checking database structure...', logger.MESSAGE)
    _process_upgrade(connection, schema)


def pretty_name(class_name):
    return ' '.join(
        [x.group() for x in re.finditer('([A-Z])([a-z0-9]+)', class_name)],
    )


def _process_upgrade(connection, upgrade_class):
    instance = upgrade_class(connection)
    logger.log(
        f'Checking {pretty_name(upgrade_class.__name__)} database upgrade',
        logger.DEBUG,
    )
    if not instance.test():
        logger.log(
            f'Database upgrade required: {pretty_name(upgrade_class.__name__)}',
            logger.MESSAGE,
        )
        try:
            instance.execute()
        except sqlite3.DatabaseError as error:
            print(
                f'Error in {upgrade_class.__name__}: {error}',
            )
            raise
        logger.log(
            f'{upgrade_class.__name__} upgrade completed',
            logger.DEBUG,
        )
    else:
        logger.log(
            f'{upgrade_class.__name__} upgrade not required',
            logger.DEBUG,
        )

    for upgradeSubClass in upgrade_class.__subclasses__():
        _process_upgrade(connection, upgradeSubClass)


# Base migration class. All future DB changes should be subclassed from this class
class SchemaUpgrade:
    def __init__(self, connection):
        self.connection = connection

    def has_table(self, table_name):
        return (
            len(
                self.connection.action(
                    'SELECT 1 FROM sqlite_master WHERE name = ?;',
                    (table_name,),
                ).fetchall(),
            )
            > 0
        )

    def has_column(self, table_name, column):
        return column in self.connection.table_info(table_name)

    def add_column(self, table, column, data_type='NUMERIC', default=0):
        self.connection.action(f'ALTER TABLE {table} ADD {column} {data_type}')
        self.connection.action(f'UPDATE {table} SET {column} = ?', (default,))

    def check_db_version(self):
        result = self.connection.select('SELECT db_version FROM db_version')
        if result:
            return int(result[-1]['db_version'])
        else:
            return 0

    def inc_db_version(self):
        new_version = self.check_db_version() + 1
        self.connection.action(
            'UPDATE db_version SET db_version = ?', [new_version],
        )
        return new_version