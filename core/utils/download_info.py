import datetime

from six import text_type

from core import logger, main_db


def update_download_info_status(input_name, status):
    logger.db('Updating status of our download {0} in the DB to {1}'.format(input_name, status))

    my_db = main_db.DBConnection()
    my_db.action('UPDATE downloads SET status=?, last_update=? WHERE input_name=?',
                 [status, datetime.date.today().toordinal(), text_type(input_name)])


def get_download_info(input_name, status):
    logger.db('Getting download info for {0} from the DB'.format(input_name))

    my_db = main_db.DBConnection()
    sql_results = my_db.select('SELECT * FROM downloads WHERE input_name=? AND status=?',
                               [text_type(input_name), status])

    return sql_results
