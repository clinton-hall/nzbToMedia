from __future__ import annotations

import logging

from deluge_client import DelugeRPCClient

import nzb2media

log = logging.getLogger()
log.addHandler(logging.NullHandler())


def configure_client():
    agent = 'deluge'
    host = nzb2media.DELUGE_HOST
    port = nzb2media.DELUGE_PORT
    user = nzb2media.DELUGE_USER
    password = nzb2media.DELUGE_PASSWORD
    log.debug(f'Connecting to {agent}: http://{host}:{port}')
    client = DelugeRPCClient(host, port, user, password)
    try:
        client.connect()
    except Exception:
        log.error('Failed to connect to Deluge')
    else:
        return client
