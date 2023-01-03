from __future__ import annotations

import datetime
import logging

import nzb2media.databases

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
database = nzb2media.databases.DBConnection()


def update_download_info_status(input_name, status):
    log.debug(f'Updating DB download status of {input_name} to {status}')
    action = 'UPDATE downloads SET status=?, last_update=? WHERE input_name=?'
    args = [status, datetime.date.today().toordinal(), input_name]
    database.action(action, args)


def get_download_info(input_name, status):
    log.debug(f'Getting download info for {input_name} from the DB')
    action = 'SELECT * FROM downloads WHERE input_name=? AND status=?'
    args = [input_name, status]
    return database.select(action, args)
