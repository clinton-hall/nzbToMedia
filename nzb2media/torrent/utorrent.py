from __future__ import annotations

import logging

from utorrent.client import UTorrentClient

import nzb2media

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def configure_client():
    agent = 'utorrent'
    web_ui = nzb2media.UTORRENT_WEB_UI
    user = nzb2media.UTORRENT_USER
    password = nzb2media.UTORRENT_PASSWORD
    log.debug(f'Connecting to {agent}: {web_ui}')
    try:
        client = UTorrentClient(web_ui, user, password)
    except Exception:
        log.error('Failed to connect to uTorrent')
        return None
    else:
        return client
