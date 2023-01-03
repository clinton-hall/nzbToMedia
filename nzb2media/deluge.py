from __future__ import annotations

import logging

from deluge_client import DelugeRPCClient

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

HOST = None
PORT = None
USERNAME = None
PASSWORD = None


def configure_deluge(config):
    global HOST
    global PORT
    global USERNAME
    global PASSWORD

    HOST = config['DelugeHost']  # localhost
    PORT = int(config['DelugePort'])  # 8084
    USERNAME = config['DelugeUSR']  # mysecretusr
    PASSWORD = config['DelugePWD']  # mysecretpwr


def configure_client():
    agent = 'deluge'
    host = HOST
    port = PORT
    user = USERNAME
    password = PASSWORD
    log.debug(f'Connecting to {agent}: http://{host}:{port}')
    client = DelugeRPCClient(host, port, user, password)
    try:
        client.connect()
    except Exception:
        log.error('Failed to connect to Deluge')
    else:
        return client
