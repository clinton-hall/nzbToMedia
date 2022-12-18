from __future__ import annotations

import logging

from syno.downloadstation import DownloadStation

import nzb2media

log = logging.getLogger(__name__)


def configure_client():
    agent = 'synology'
    host = nzb2media.SYNO_HOST
    port = nzb2media.SYNO_PORT
    user = nzb2media.SYNO_USER
    password = nzb2media.SYNO_PASSWORD
    log.debug(f'Connecting to {agent}: http://{host}:{port}')
    try:
        client = DownloadStation(host, port, user, password)
    except Exception:
        log.error('Failed to connect to synology')
    else:
        return client
