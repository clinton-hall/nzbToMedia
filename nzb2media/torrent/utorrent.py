from __future__ import annotations

from utorrent.client import UTorrentClient

import nzb2media


def configure_client():
    agent = 'utorrent'
    web_ui = nzb2media.UTORRENT_WEB_UI
    user = nzb2media.UTORRENT_USER
    password = nzb2media.UTORRENT_PASSWORD

    logger.debug(f'Connecting to {agent}: {web_ui}')
    try:
        client = UTorrentClient(web_ui, user, password)
    except Exception:
        logger.error('Failed to connect to uTorrent')
    else:
        return client
