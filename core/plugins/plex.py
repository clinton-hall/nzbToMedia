from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import requests

import core
from core import logger


def configure_plex(config):
    core.PLEX_SSL = int(config['Plex']['plex_ssl'])
    core.PLEX_HOST = config['Plex']['plex_host']
    core.PLEX_PORT = config['Plex']['plex_port']
    core.PLEX_TOKEN = config['Plex']['plex_token']
    plex_section = config['Plex']['plex_sections'] or []

    if plex_section:
        if isinstance(plex_section, list):
            plex_section = ','.join(plex_section)  # fix in case this imported as list.
        plex_section = [
            tuple(item.split(','))
            for item in plex_section.split('|')
        ]

    core.PLEX_SECTION = plex_section


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
