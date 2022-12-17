from __future__ import annotations

from deluge_client import DelugeRPCClient

import nzb2media


def configure_client():
    agent = 'deluge'
    host = nzb2media.DELUGE_HOST
    port = nzb2media.DELUGE_PORT
    user = nzb2media.DELUGE_USER
    password = nzb2media.DELUGE_PASSWORD

    logger.debug(f'Connecting to {agent}: http://{host}:{port}')
    client = DelugeRPCClient(host, port, user, password)
    try:
        client.connect()
    except Exception:
        logger.error('Failed to connect to Deluge')
    else:
        return client
