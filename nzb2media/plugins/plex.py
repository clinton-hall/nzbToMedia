from __future__ import annotations

import logging

import requests

import nzb2media

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def configure_plex(config):
    nzb2media.PLEX_SSL = int(config['Plex']['plex_ssl'])
    nzb2media.PLEX_HOST = config['Plex']['plex_host']
    nzb2media.PLEX_PORT = config['Plex']['plex_port']
    nzb2media.PLEX_TOKEN = config['Plex']['plex_token']
    plex_section = config['Plex']['plex_sections'] or []
    if plex_section:
        if isinstance(plex_section, list):
            plex_section = ','.join(plex_section)  # fix in case this imported as list.
        plex_section = [tuple(item.split(',')) for item in plex_section.split('|')]
    nzb2media.PLEX_SECTION = plex_section


def plex_update(category):
    if nzb2media.FAILED:
        return
    scheme = 'https' if nzb2media.PLEX_SSL else 'http'
    url = f'{scheme}://{nzb2media.PLEX_HOST}:{nzb2media.PLEX_PORT}/library/sections/'
    section = None
    if not nzb2media.PLEX_SECTION:
        return
    log.debug(f'Attempting to update Plex Library for category {category}.')
    for item in nzb2media.PLEX_SECTION:
        if item[0] == category:
            section = item[1]
    if section:
        url = f'{url}{section}/refresh?X-Plex-Token={nzb2media.PLEX_TOKEN}'
        requests.get(url, timeout=(60, 120), verify=False)
        log.debug('Plex Library has been refreshed.')
    else:
        log.debug('Could not identify SECTION for plex update')
