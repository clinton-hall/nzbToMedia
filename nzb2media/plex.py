from __future__ import annotations

import logging

import requests

import nzb2media

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

SSL = None
HOST = None
PORT = None
TOKEN = None
SECTION: list[tuple[str, str]] = []


def configure_plex(config):
    global SSL
    global HOST
    global PORT
    global TOKEN
    global SECTION

    SSL = int(config['Plex']['plex_ssl'])
    HOST = config['Plex']['plex_host']
    PORT = config['Plex']['plex_port']
    TOKEN = config['Plex']['plex_token']
    plex_section = config['Plex']['plex_sections'] or []
    if plex_section:
        if isinstance(plex_section, list):
            plex_section = ','.join(plex_section)  # fix in case this imported as list.
        plex_section = [tuple(item.split(',')) for item in plex_section.split('|')]
    SECTION = plex_section


def plex_update(category):
    if nzb2media.FAILED:
        return
    scheme = 'https' if SSL else 'http'
    url = f'{scheme}://{HOST}:{PORT}/library/sections/'
    section = None
    if not SECTION:
        return
    log.debug(f'Attempting to update Plex Library for category {category}.')
    for item in SECTION:
        if item[0] == category:
            section = item[1]
    if section:
        url = f'{url}{section}/refresh?X-Plex-Token={TOKEN}'
        requests.get(url, timeout=(60, 120), verify=False)
        log.debug('Plex Library has been refreshed.')
    else:
        log.debug('Could not identify SECTION for plex update')
