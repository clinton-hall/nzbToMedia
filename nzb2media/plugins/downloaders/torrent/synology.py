from __future__ import annotations

from syno.downloadstation import DownloadStation

import nzb2media
from nzb2media import logger


def configure_client():
    agent = 'synology'
    host = nzb2media.SYNO_HOST
    port = nzb2media.SYNO_PORT
    user = nzb2media.SYNO_USER
    password = nzb2media.SYNO_PASSWORD

    logger.debug(f'Connecting to {agent}: http://{host}:{port}')
    try:
        client = DownloadStation(host, port, user, password)
    except Exception:
        logger.error('Failed to connect to synology')
    else:
        return client
