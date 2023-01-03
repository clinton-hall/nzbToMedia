from __future__ import annotations

import logging

from syno.downloadstation import DownloadStation

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

HOST = None
PORT = None
USERNAME = None
PASSWORD = None


def configure_syno(config):
    global HOST
    global PORT
    global USERNAME
    global PASSWORD

    HOST = config['synoHost']  # localhost
    PORT = int(config['synoPort'])
    USERNAME = config['synoUSR']  # mysecretusr
    PASSWORD = config['synoPWD']  # mysecretpwr


def configure_client():
    agent = 'synology'
    host = HOST
    port = PORT
    user = USERNAME
    password = PASSWORD
    log.debug(f'Connecting to {agent}: http://{host}:{port}')
    try:
        client = DownloadStation(host, port, user, password)
    except Exception:
        log.error('Failed to connect to synology')
    else:
        return client
