from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from utorrent.client import UTorrentClient

import core
from core import logger


def configure_client():
    agent = 'utorrent'
    web_ui = core.UTORRENT_WEB_UI
    user = core.UTORRENT_USER
    password = core.UTORRENT_PASSWORD

    logger.debug('Connecting to {0}: {1}'.format(agent, web_ui))
    try:
        client = UTorrentClient(web_ui, user, password)
    except Exception:
        logger.error('Failed to connect to uTorrent')
    else:
        return client
