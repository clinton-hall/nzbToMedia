import requests

import core
from core import logger


def plex_update(category):
    if core.FAILED:
        return
    url = '{scheme}://{host}:{port}/library/sections/'.format(
        scheme='https' if core.PLEXSSL else 'http',
        host=core.PLEXHOST,
        port=core.PLEXPORT,
    )
    section = None
    if not core.PLEXSEC:
        return
    logger.debug('Attempting to update Plex Library for category {0}.'.format(category), 'PLEX')
    for item in core.PLEXSEC:
        if item[0] == category:
            section = item[1]

    if section:
        url = '{url}{section}/refresh?X-Plex-Token={token}'.format(url=url, section=section, token=core.PLEXTOKEN)
        requests.get(url, timeout=(60, 120), verify=False)
        logger.debug('Plex Library has been refreshed.', 'PLEX')
    else:
        logger.debug('Could not identify section for plex update', 'PLEX')


