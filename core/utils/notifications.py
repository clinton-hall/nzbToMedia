import requests

import core
from core import logger


def plex_update(category):
    if core.FAILED:
        return
    url = '{scheme}://{host}:{port}/library/sections/'.format(
        scheme='https' if core.PLEX_SSL else 'http',
        host=core.PLEX_HOST,
        port=core.PLEX_PORT,
    )
    section = None
    if not core.PLEX_SECTION:
        return
    logger.debug('Attempting to update Plex Library for category {0}.'.format(category), 'PLEX')
    for item in core.PLEX_SECTION:
        if item[0] == category:
            section = item[1]

    if section:
        url = '{url}{section}/refresh?X-Plex-Token={token}'.format(url=url, section=section, token=core.PLEX_TOKEN)
        requests.get(url, timeout=(60, 120), verify=False)
        logger.debug('Plex Library has been refreshed.', 'PLEX')
    else:
        logger.debug('Could not identify section for plex update', 'PLEX')


