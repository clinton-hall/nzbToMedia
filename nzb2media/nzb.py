from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

CLIENTS = ['sabnzbd', 'nzbget', 'manual']
CLIENT_AGENT = None
DEFAULT_DIRECTORY = None
NO_MANUAL = None

SABNZBD_HOST = ''
SABNZBD_PORT = None
SABNZBD_APIKEY = None


def configure_nzbs(config):
    global CLIENT_AGENT
    global DEFAULT_DIRECTORY
    global NO_MANUAL

    nzb_config = config['Nzb']
    CLIENT_AGENT = nzb_config['clientAgent']  # sabnzbd
    DEFAULT_DIRECTORY = nzb_config['default_downloadDirectory']
    NO_MANUAL = int(nzb_config['no_manual'], 0)
    configure_sabnzbd(nzb_config)


def configure_sabnzbd(config):
    global SABNZBD_HOST
    global SABNZBD_PORT
    global SABNZBD_APIKEY

    SABNZBD_HOST = config['sabnzbd_host']
    # defaults to accommodate NzbGet
    SABNZBD_PORT = int(config['sabnzbd_port'] or 8080)
    SABNZBD_APIKEY = config['sabnzbd_apikey']


def get_nzoid(input_name):
    nzoid = None
    slots = []
    log.debug('Searching for nzoid from SAbnzbd ...')
    if 'http' in SABNZBD_HOST:
        base_url = f'{SABNZBD_HOST}:{SABNZBD_PORT}/api'
    else:
        base_url = f'http://{SABNZBD_HOST}:{SABNZBD_PORT}/api'
    url = base_url
    params = {'apikey': SABNZBD_APIKEY, 'mode': 'queue', 'output': 'json'}
    try:
        response = requests.get(url, params=params, verify=False, timeout=(30, 120))
    except requests.ConnectionError:
        log.error('Unable to open URL')
        return nzoid  # failure
    try:
        result = response.json()
        clean_name = os.path.splitext(os.path.split(input_name)[1])[0]
        slots.extend([(slot['nzo_id'], slot['filename']) for slot in result['queue']['slots']])
    except Exception:
        log.warning('Data from SABnzbd queue could not be parsed')
    params['mode'] = 'history'
    try:
        response = requests.get(url, params=params, verify=False, timeout=(30, 120))
    except requests.ConnectionError:
        log.error('Unable to open URL')
        return nzoid  # failure
    try:
        result = response.json()
        clean_name = os.path.splitext(os.path.split(input_name)[1])[0]
        slots.extend([(slot['nzo_id'], slot['name']) for slot in result['history']['slots']])
    except Exception:
        log.warning('Data from SABnzbd history could not be parsed')
    try:
        for nzo_id, name in slots:
            if name in [input_name, clean_name]:
                nzoid = nzo_id
                log.debug(f'Found nzoid: {nzoid}')
                break
    except Exception:
        log.warning('Data from SABnzbd could not be parsed')
    return nzoid


def report_nzb(failure_link, client_agent):
    # Contact indexer site
    log.info('Sending failure notification to indexer site')
    if client_agent == 'nzbget':
        headers = {'User-Agent': 'NZBGet / nzbToMedia.py'}
    elif client_agent == 'sabnzbd':
        headers = {'User-Agent': 'SABnzbd / nzbToMedia.py'}
    else:
        return
    try:
        requests.post(failure_link, headers=headers, timeout=(30, 300))
    except Exception as error:
        log.error(f'Unable to open URL {failure_link} due to {error}')
    return
