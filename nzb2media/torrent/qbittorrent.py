from __future__ import annotations

from qbittorrent import Client as qBittorrentClient

import nzb2media


def configure_client():
    agent = 'qbittorrent'
    host = nzb2media.QBITTORRENT_HOST
    port = nzb2media.QBITTORRENT_PORT
    user = nzb2media.QBITTORRENT_USER
    password = nzb2media.QBITTORRENT_PASSWORD

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
