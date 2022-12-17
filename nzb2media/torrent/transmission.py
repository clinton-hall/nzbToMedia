from __future__ import annotations

import logging

from transmissionrpc.client import Client as TransmissionClient

import nzb2media

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def configure_client():
    agent = 'transmission'
    host = nzb2media.TRANSMISSION_HOST
    port = nzb2media.TRANSMISSION_PORT
    user = nzb2media.TRANSMISSION_USER
    password = nzb2media.TRANSMISSION_PASSWORD

    log.debug(f'Connecting to {agent}: http://{host}:{port}')
    try:
        client = TransmissionClient(host, port, user, password)
    except Exception:
        log.error('Failed to connect to Transmission')
    else:
        return client
