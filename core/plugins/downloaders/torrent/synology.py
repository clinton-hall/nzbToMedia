from __future__ import annotations

from syno.downloadstation import DownloadStation

import core
from core import logger


def configure_client():
    agent = 'synology'
    host = core.SYNO_HOST
    port = core.SYNO_PORT
    user = core.SYNO_USER
    password = core.SYNO_PASSWORD

    logger.debug(f'Connecting to {agent}: http://{host}:{port}')
    try:
        client = DownloadStation(host, port, user, password)
    except Exception:
        logger.error('Failed to connect to synology')
    else:
        return client
