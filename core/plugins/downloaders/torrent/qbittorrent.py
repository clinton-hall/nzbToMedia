from __future__ import annotations

from qbittorrent import Client as qBittorrentClient

import core
from core import logger


def configure_client():
    agent = 'qbittorrent'
    host = core.QBITTORRENT_HOST
    port = core.QBITTORRENT_PORT
    user = core.QBITTORRENT_USER
    password = core.QBITTORRENT_PASSWORD

    logger.debug(
        f'Connecting to {agent}: http://{host}:{port}',
    )
    client = qBittorrentClient(f'http://{host}:{port}/')
    try:
        client.login(user, password)
    except Exception:
        logger.error('Failed to connect to qBittorrent')
    else:
        return client
