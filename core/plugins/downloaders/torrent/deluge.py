from synchronousdeluge.client import DelugeClient

import core
from core import logger


def configure_client():
    agent = 'deluge'
    host = core.DELUGE_HOST
    port = core.DELUGE_PORT
    user = core.DELUGE_USER
    password = core.DELUGE_PASSWORD

    logger.debug('Connecting to {0}: http://{1}:{2}'.format(agent, host, port))
    client = DelugeClient()
    try:
        client.connect(host, port, user, password)
    except Exception:
        logger.error('Failed to connect to Deluge')
    else:
        return client
