# coding=utf-8

from core import logger, nzbToMediaDB
from core.nzbToMediaUtil import backupVersionedFile

MIN_DB_VERSION = 1  # oldest db version we support migrating from
MAX_DB_VERSION = 2


def backupDatabase(version):
    logger.info("Backing up database before upgrade")
    if not backupVersionedFile(nzbToMediaDB.dbFilename(), version):
        logger.log_error_and_exit("Database backup failed, abort upgrading database")
    else:
        logger.info("Proceeding with upgrade")


# ======================
# = Main DB Migrations =
# ======================
# Add new migrations at the bottom of the list; subclass the previous migration.

class InitialSchema(nzbToMediaDB.SchemaUpgrade):
    def test(self):
        no_update = False
        if self.hasTable("db_version"):
            cur_db_version = self.checkDBVersion()
            no_update = not cur_db_version < MAX_DB_VERSION
        return no_update

    def execute(self):
        if not self.hasTable("downloads") and not self.hasTable("db_version"):
            queries = [
                "CREATE TABLE db_version (db_version INTEGER);",
                "CREATE TABLE downloads (input_directory TEXT, input_name TEXT, input_hash TEXT, input_id TEXT, client_agent TEXT, status INTEGER, last_update NUMERIC, CONSTRAINT pk_downloadID PRIMARY KEY (input_directory, input_name));",
                "INSERT INTO db_version (db_version) VALUES (2);"
            ]
            for query in queries:
                self.connection.action(query)

        else:
            cur_db_version = self.checkDBVersion()

            if cur_db_version < MIN_DB_VERSION:
                logger.log_error_and_exit(u"Your database version ({current}) is too old to migrate "
                                          u"from what this version of nzbToMedia supports ({min})."
                                          u"\nPlease remove nzbtomedia.db file to begin fresh.".format
                                          (current=cur_db_version, min=MIN_DB_VERSION))

            if cur_db_version > MAX_DB_VERSION:
                logger.log_error_and_exit(u"Your database version ({current}) has been incremented "
                                          u"past what this version of nzbToMedia supports ({max})."
                                          u"\nIf you have used other forks of nzbToMedia, your database "
                                          u"may be unusable due to their modifications.".format
                                          (current=cur_db_version, max=MAX_DB_VERSION))
            if cur_db_version < MAX_DB_VERSION:  # We need to upgrade.
                queries = [
                    "CREATE TABLE downloads2 (input_directory TEXT, input_name TEXT, input_hash TEXT, input_id TEXT, client_agent TEXT, status INTEGER, last_update NUMERIC, CONSTRAINT pk_downloadID PRIMARY KEY (input_directory, input_name));",
                    "INSERT INTO downloads2 SELECT * FROM downloads;",
                    "DROP TABLE IF EXISTS downloads;",
                    "ALTER TABLE downloads2 RENAME TO downloads;",
                    "INSERT INTO db_version (db_version) VALUES (2);"
                ]
                for query in queries:
                    self.connection.action(query)
