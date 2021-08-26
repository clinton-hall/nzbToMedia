from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from syno.downloadstation import DownloadStation

import core
from core import logger


def configure_client():
    agent = 'synology'
    host = core.SYNO_HOST
    port = core.SYNO_PORT
    user = core.SYNO_USER
    password = core.SYNO_PASSWORD

    logger.debug('Connecting to {0}: http://{1}:{2}'.format(agent, host, port))
    try:
        client = DownloadStation(host, port, user, password)
    except Exception:
        logger.error('Failed to connect to synology')
    else:
        return client
