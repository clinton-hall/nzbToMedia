from __future__ import annotations

import logging

from qbittorrent import Client as qBittorrentClient

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

HOST = None
PORT = None
USERNAME = None
PASSWORD = None


def configure_qbittorrent(config):
    global HOST
    global PORT
    global USERNAME
    global PASSWORD

    HOST = config['qBittorrentHost']  # localhost
    PORT = int(config['qBittorrentPort'])  # 8080
    USERNAME = config['qBittorrentUSR']  # mysecretusr
    PASSWORD = config['qBittorrentPWD']  # mysecretpwr


def configure_client():
    agent = 'qbittorrent'
    host = HOST
    port = PORT
    user = USERNAME
    password = PASSWORD
    log.debug(f'Connecting to {agent}: http://{host}:{port}')
    client = qBittorrentClient(f'http://{host}:{port}/')
    try:
        client.login(user, password)
    except Exception:
        log.error('Failed to connect to qBittorrent')
    else:
        return client
