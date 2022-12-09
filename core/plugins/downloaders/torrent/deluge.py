from __future__ import annotations

from deluge_client import DelugeRPCClient

import core
from core import logger


def configure_client():
    agent = 'deluge'
    host = core.DELUGE_HOST
    port = core.DELUGE_PORT
    user = core.DELUGE_USER
    password = core.DELUGE_PASSWORD

    logger.debug(f'Connecting to {agent}: http://{host}:{port}')
    client = DelugeRPCClient(host, port, user, password)
    try:
        client.connect()
    except Exception:
        logger.error('Failed to connect to Deluge')
    else:
        return client
