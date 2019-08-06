from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


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
        'Connecting to {0}: http://{1}:{2}'.format(agent, host, port),
    )
    client = qBittorrentClient('http://{0}:{1}/'.format(host, port))
    try:
        client.login(user, password)
    except Exception:
        logger.error('Failed to connect to qBittorrent')
    else:
        return client
