from __future__ import annotations

import logging

from utorrent.client import UTorrentClient

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

HOST = None
USERNAME = None
PASSWORD = None


def configure_utorrent(config):
    global HOST
    global USERNAME
    global PASSWORD

    HOST = config['uTorrentWEBui']  # http://localhost:8090/gui/
    USERNAME = config['uTorrentUSR']  # mysecretusr
    PASSWORD = config['uTorrentPWD']  # mysecretpwr


def configure_client():
    agent = 'utorrent'
    web_ui = HOST
    user = USERNAME
    password = PASSWORD
    log.debug(f'Connecting to {agent}: {web_ui}')
    try:
        client = UTorrentClient(web_ui, user, password)
    except Exception:
        log.error('Failed to connect to uTorrent')
        return None
    else:
        return client
