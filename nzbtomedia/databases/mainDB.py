import nzbtomedia
from nzbtomedia import logger, nzbToMediaDB
from nzbtomedia.nzbToMediaUtil import backupVersionedFile

MIN_DB_VERSION = 1  # oldest db version we support migrating from
MAX_DB_VERSION = 1

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
        return self.hasTable("db_version")

    def execute(self):
        if not self.hasTable("history") and not self.hasTable("db_version"):
            queries = [
                "CREATE TABLE db_version (db_version INTEGER);",
                "CREATE TABLE downloads (input_directory TEXT, input_name TEXT PRIMARY KEY, input_hash TEXT, input_id TEXT, client_agent TEXT, status INTEGER, last_update NUMERIC);",
                "INSERT INTO db_version (db_version) VALUES (1);"
            ]
            for query in queries:
                self.connection.action(query)

        else:
            cur_db_version = self.checkDBVersion()

            if cur_db_version < MIN_DB_VERSION:
                logger.log_error_and_exit("Your database version (" + str(
                    cur_db_version) + ") is too old to migrate from what this version of nzbToMedia supports (" + \
                                          str(MIN_DB_VERSION) + ").\n" + \
                                          "Please remove nzbtomedia.db file to begin fresh."
                )

            if cur_db_version > MAX_DB_VERSION:
                logger.log_error_and_exit("Your database version (" + str(
                    cur_db_version) + ") has been incremented past what this version of nzbToMedia supports (" + \
                                          str(MAX_DB_VERSION) + ").\n" + \
                                          "If you have used other forks of nzbToMedia, your database may be unusable due to their modifications."
                )