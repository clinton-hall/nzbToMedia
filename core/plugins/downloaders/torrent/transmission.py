from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from transmissionrpc.client import Client as TransmissionClient

import core
from core import logger


def configure_client():
    agent = 'transmission'
    host = core.TRANSMISSION_HOST
    port = core.TRANSMISSION_PORT
    user = core.TRANSMISSION_USER
    password = core.TRANSMISSION_PASSWORD

    logger.debug('Connecting to {0}: http://{1}:{2}'.format(agent, host, port))
    try:
        client = TransmissionClient(host, port, user, password)
    except Exception:
        logger.error('Failed to connect to Transmission')
    else:
        return client
