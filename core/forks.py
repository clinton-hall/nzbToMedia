# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import requests
import six
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session
from six import iteritems

import core
from core import logger

from core.auto_process.managers.sickbeard import InitSickBeard


def auto_fork(section, input_category):
    # auto-detect correct section
    # config settings
    if core.FORK_SET:  # keep using determined fork for multiple (manual) post-processing
        logger.info('{section}:{category} fork already set to {fork}'.format
                    (section=section, category=input_category, fork=core.FORK_SET[0]))
        return core.FORK_SET[0], core.FORK_SET[1]

    cfg = dict(core.CFG[section][input_category])

    # Refactor into an OO structure.
    # For now let's do botch the OO and the serialized code, until everything has been migrated.
    init_sickbeard = InitSickBeard(cfg, section, input_category)

    host = cfg.get('host')
    port = cfg.get('port')
    username = cfg.get('username', '')
    password = cfg.get('password', '')
    sso_username = cfg.get('sso_username', '')
    sso_password = cfg.get('sso_password', '')
    apikey = cfg.get('apikey', '')
    api_version = int(cfg.get('api_version', 2))
    ssl = int(cfg.get('ssl', 0))
    web_root = cfg.get('web_root', '')
    replace = {
        'medusa': 'Medusa',
        'medusa-api': 'Medusa-api',
        'sickbeard-api': 'SickBeard-api',
        'sickgear': 'SickGear',
        'sickchill': 'SickChill',
        'stheno': 'Stheno',
    }
    _val = cfg.get('fork', 'auto')
    f1 = replace.get(_val, _val)
    try:
        fork = f1, core.FORKS[f1]
    except KeyError:
        fork = 'auto'
    protocol = 'https://' if ssl else 'http://'

    detected = False
    if section == 'NzbDrone':
        logger.info('Attempting to verify {category} fork'.format
                    (category=input_category))
        url = '{protocol}{host}:{port}{root}/api/rootfolder'.format(
            protocol=protocol, host=host, port=port, root=web_root,
        )
        headers = {'X-Api-Key': apikey}
        try:
            r = requests.get(url, headers=headers, stream=True, verify=False)
        except requests.ConnectionError:
            logger.warning('Could not connect to {0}:{1} to verify fork!'.format(section, input_category))

        if not r.ok:
            logger.warning('Connection to {section}:{category} failed! '
                           'Check your configuration'.format
                           (section=section, category=input_category))

        fork = ['default', {}]

    elif section == 'SiCKRAGE':
        logger.info('Attempting to verify {category} fork'.format
                    (category=input_category))

        if api_version >= 2:
            url = '{protocol}{host}:{port}{root}/api/v{api_version}/ping'.format(
                protocol=protocol, host=host, port=port, root=web_root, api_version=api_version
            )
            api_params = {}
        else:
            url = '{protocol}{host}:{port}{root}/api/v{api_version}/{apikey}/'.format(
                protocol=protocol, host=host, port=port, root=web_root, api_version=api_version, apikey=apikey,
            )
            api_params = {'cmd': 'postprocess', 'help': '1'}

        try:
            if api_version >= 2 and sso_username and sso_password:
                oauth = OAuth2Session(client=LegacyApplicationClient(client_id=core.SICKRAGE_OAUTH_CLIENT_ID))
                oauth_token = oauth.fetch_token(client_id=core.SICKRAGE_OAUTH_CLIENT_ID,
                                                token_url=core.SICKRAGE_OAUTH_TOKEN_URL,
                                                username=sso_username,
                                                password=sso_password)
                r = requests.get(url, headers={'Authorization': 'Bearer ' + oauth_token['access_token']}, stream=True, verify=False)
            else:
                r = requests.get(url, params=api_params, stream=True, verify=False)

            if not r.ok:
                logger.warning('Connection to {section}:{category} failed! '
                               'Check your configuration'.format
                               (section=section, category=input_category))
        except requests.ConnectionError:
            logger.warning('Could not connect to {0}:{1} to verify API version!'.format(section, input_category))

        params = {
            'path': None,
            'failed': None,
            'process_method': None,
            'force_replace': None,
            'return_data': None,
            'type': None,
            'delete': None,
            'force_next': None,
            'is_priority': None
        }

        fork = ['default', params]

    elif fork == 'auto':
        fork = init_sickbeard.detect_fork()

    logger.info('{section}:{category} fork set to {fork}'.format
                (section=section, category=input_category, fork=fork[0]))
    core.FORK_SET = fork
    return fork[0], fork[1]
