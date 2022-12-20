from __future__ import annotations

import logging

from transmission_rpc.client import Client as TransmissionClient

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

HOST = None
PORT = None
USERNAME = None
PASSWORD = None


def configure_transmission(config):
    global HOST
    global PORT
    global USERNAME
    global PASSWORD

    HOST = config['TransmissionHost']  # localhost
    PORT = int(config['TransmissionPort'])
    USERNAME = config['TransmissionUSR']  # mysecretusr
    PASSWORD = config['TransmissionPWD']  # mysecretpwr


def configure_client():
    agent = 'transmission'
    host = HOST
    port = PORT
    user = USERNAME
    password = PASSWORD
    log.debug(f'Connecting to {agent}: http://{host}:{port}')
    try:
        client = TransmissionClient(
            host=host or '127.0.0.1',
            port=port or 9091,
            username=user,
            password=password,
        )
    except Exception:
        log.error('Failed to connect to Transmission')
    else:
        return client
