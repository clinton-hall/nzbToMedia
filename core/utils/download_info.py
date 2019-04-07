from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import datetime

from six import text_type

from core import logger, main_db

database = main_db.DBConnection()


def update_download_info_status(input_name, status):
    msg = 'Updating DB download status of {0} to {1}'
    action = 'UPDATE downloads SET status=?, last_update=? WHERE input_name=?'
    args = [status, datetime.date.today().toordinal(), text_type(input_name)]
    logger.db(msg.format(input_name, status))
    database.action(action, args)


def get_download_info(input_name, status):
    msg = 'Getting download info for {0} from the DB'
    action = 'SELECT * FROM downloads WHERE input_name=? AND status=?'
    args = [text_type(input_name), status]
    logger.db(msg.format(input_name))
    return database.select(action, args)
