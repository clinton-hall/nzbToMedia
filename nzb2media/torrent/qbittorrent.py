from __future__ import annotations

import logging

from qbittorrent import Client as qBittorrentClient

import nzb2media

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def configure_client():
    agent = 'qbittorrent'
    host = nzb2media.QBITTORRENT_HOST
    port = nzb2media.QBITTORRENT_PORT
    user = nzb2media.QBITTORRENT_USER
    password = nzb2media.QBITTORRENT_PASSWORD

    log.debug(f'Connecting to {agent}: http://{host}:{port}')
    client = qBittorrentClient(f'http://{host}:{port}/')
    try:
        client.login(user, password)
    except Exception:
        log.error('Failed to connect to qBittorrent')
    else:
        return client
