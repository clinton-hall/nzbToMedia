# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import core
from core import logger

from oauthlib.oauth2 import LegacyApplicationClient

import requests

from requests_oauthlib import OAuth2Session

import six
from six import iteritems


class InitSickBeard(object):
    """Sickbeard init class.

    Used to determin which sickbeard fork object to initialize.
    """

    def __init__(self, cfg, section, input_category):
        # As a bonus let's also put the config on self.
        self.config = cfg
        self.section = section
        self.input_category = input_category

        self.host = cfg['host']
        self.port = cfg['port']
        self.ssl = int(cfg.get('ssl', 0))
        self.web_root = cfg.get('web_root', '')
        self.protocol = 'https://' if self.ssl else 'http://'
        self.username = cfg.get('username', '')
        self.password = cfg.get('password', '')
        self.apikey = cfg.get('apikey', '')
        self.api_version = int(cfg.get('api_version', 2))
        self.sso_username = cfg.get('sso_username', '')
        self.sso_password = cfg.get('sso_password', '')

        self.fork = 'auto'

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
            self.fork = f1, core.FORKS[f1]
        except KeyError:
            self.fork = 'auto'
            self.protocol = 'https://' if self.ssl else 'http://'

    def auto_fork(self):
        # auto-detect correct section
        # config settings
        if core.FORK_SET:  # keep using determined fork for multiple (manual) post-processing
            logger.info('{section}:{category} fork already set to {fork}'.format
                        (section=self.section, category=self.input_category, fork=core.FORK_SET[0]))
            return core.FORK_SET[0], core.FORK_SET[1]

        cfg = dict(core.CFG[self.section][self.input_category])

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
        protocol = 'https://' if self.ssl else 'http://'

        if self.section == 'NzbDrone':
            logger.info('Attempting to verify {category} fork'.format
                        (category=self.input_category))
            url = '{protocol}{host}:{port}{root}/api/rootfolder'.format(
                protocol=protocol, host=self.host, port=self.port, root=self.web_root,
            )
            headers = {'X-Api-Key': self.apikey}
            try:
                r = requests.get(url, headers=headers, stream=True, verify=False)
            except requests.ConnectionError:
                logger.warning('Could not connect to {0}:{1} to verify fork!'.format(self.section, self.input_category))

            if not r.ok:
                logger.warning('Connection to {section}:{category} failed! '
                               'Check your configuration'.format
                               (section=self.section, category=self.input_category))

            fork = ['default', {}]

        elif self.section == 'SiCKRAGE':
            logger.info('Attempting to verify {category} fork'.format
                        (category=self.input_category))

            if self.api_version >= 2:
                url = '{protocol}{host}:{port}{root}/api/v{api_version}/ping'.format(
                    protocol=protocol, host=self.host, port=self.port, root=self.web_root, api_version=self.api_version
                )
                api_params = {}
            else:
                url = '{protocol}{host}:{port}{root}/api/v{api_version}/{apikey}/'.format(
                    protocol=protocol, host=self.host, port=self.port, root=self.web_root, api_version=self.api_version, apikey=self.apikey,
                )
                api_params = {'cmd': 'postprocess', 'help': '1'}

            try:
                if self.api_version >= 2 and self.sso_username and self.sso_password:
                    oauth = OAuth2Session(client=LegacyApplicationClient(client_id=core.SICKRAGE_OAUTH_CLIENT_ID))
                    oauth_token = oauth.fetch_token(client_id=core.SICKRAGE_OAUTH_CLIENT_ID,
                                                    token_url=core.SICKRAGE_OAUTH_TOKEN_URL,
                                                    username=self.sso_username,
                                                    password=self.sso_password)
                    r = requests.get(url, headers={'Authorization': 'Bearer ' + oauth_token['access_token']}, stream=True, verify=False)
                else:
                    r = requests.get(url, params=api_params, stream=True, verify=False)

                if not r.ok:
                    logger.warning('Connection to {section}:{category} failed! '
                                   'Check your configuration'.format(
                                       section=self.section, category=self.input_category
                                   ))
            except requests.ConnectionError:
                logger.warning('Could not connect to {0}:{1} to verify API version!'.format(self.section, self.input_category))

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
            fork = self.detect_fork()

        logger.info('{section}:{category} fork set to {fork}'.format
                    (section=self.section, category=self.input_category, fork=fork[0]))
        core.FORK_SET = fork
        return fork[0], fork[1]

    @staticmethod
    def _api_check(r, params, rem_params):
        try:
            json_data = r.json()
        except ValueError:
            logger.error('Failed to get JSON data from response')
            logger.debug('Response received')
            raise

        try:
            json_data = json_data['data']
        except KeyError:
            logger.error('Failed to get data from JSON')
            logger.debug('Response received: {}'.format(json_data))
            raise
        else:
            if six.PY3:
                str_type = (str)
            else:
                str_type = (str, unicode)
            if isinstance(json_data, str_type):
                return rem_params, False
            json_data = json_data.get('data', json_data)

        try:
            optional_parameters = json_data['optionalParameters'].keys()
            # Find excess parameters
            excess_parameters = set(params).difference(optional_parameters)
            excess_parameters.remove('cmd')  # Don't remove cmd from api params
            logger.debug('Removing excess parameters: {}'.format(sorted(excess_parameters)))
            rem_params.extend(excess_parameters)
            return rem_params, True
        except:
            logger.error('Failed to identify optionalParameters')
            return rem_params, False

    def detect_fork(self):
        """Try to detect a specific fork."""
        detected = False
        params = core.ALL_FORKS
        rem_params = []
        logger.info('Attempting to auto-detect {category} fork'.format(category=self.input_category))
        # define the order to test. Default must be first since the default fork doesn't reject parameters.
        # then in order of most unique parameters.

        if self.apikey:
            url = '{protocol}{host}:{port}{root}/api/{apikey}/'.format(
                protocol=self.protocol, host=self.host, port=self.port, root=self.web_root, apikey=self.apikey,
            )
            api_params = {'cmd': 'sg.postprocess', 'help': '1'}
        else:
            url = '{protocol}{host}:{port}{root}/home/postprocess/'.format(
                protocol=self.protocol, host=self.host, port=self.port, root=self.web_root,
            )
            api_params = {}

        # attempting to auto-detect fork
        try:
            s = requests.Session()

            if not self.apikey and self.username and self.password:
                login = '{protocol}{host}:{port}{root}/login'.format(
                    protocol=self.protocol, host=self.host, port=self.port, root=self.web_root)
                login_params = {'username': self.username, 'password': self.password}
                r = s.get(login, verify=False, timeout=(30, 60))
                if r.status_code in [401, 403] and r.cookies.get('_xsrf'):
                    login_params['_xsrf'] = r.cookies.get('_xsrf')
                s.post(login, data=login_params, stream=True, verify=False)
            r = s.get(url, auth=(self.username, self.password), params=api_params, verify=False)
        except requests.ConnectionError:
            logger.info('Could not connect to {section}:{category} to perform auto-fork detection!'.format
                        (section=self.section, category=self.input_category))
            r = []

        if r and r.ok:
            if self.apikey:
                rem_params, found = self._api_check(r, params, rem_params)
                if found:
                    params['cmd'] = 'sg.postprocess'
                else:  # try different api set for non-SickGear forks.
                    api_params = {'cmd': 'help', 'subject': 'postprocess'}
                    try:
                        if not self.apikey and self.username and self.password:
                            r = s.get(url, auth=(self.username, self.password), params=api_params, verify=False)
                        else:
                            r = s.get(url, params=api_params, verify=False)
                    except requests.ConnectionError:
                        logger.info('Could not connect to {section}:{category} to perform auto-fork detection!'.format
                                    (section=self.section, category=self.input_category))
                    rem_params, found = self._api_check(r, params, rem_params)
                    params['cmd'] = 'postprocess'
            else:
                # Find excess parameters
                rem_params.extend(
                    param
                    for param in params
                    if 'name="{param}"'.format(param=param) not in r.text
                )

            # Remove excess params
            for param in rem_params:
                params.pop(param)

            for fork in sorted(iteritems(core.FORKS), reverse=False):
                if params == fork[1]:
                    detected = True
                    break

        if detected:
            logger.info('{section}:{category} fork auto-detection successful ...'.format
                        (section=self.section, category=self.input_category))
        elif rem_params:
            logger.info('{section}:{category} fork auto-detection found custom params {params}'.format
                        (section=self.section, category=self.input_category, params=params))
            fork = ['custom', params]
        else:
            logger.info('{section}:{category} fork auto-detection failed'.format
                        (section=self.section, category=self.input_category))
            fork = list(core.FORKS.items())[list(core.FORKS.keys()).index(core.FORK_DEFAULT)]

        return fork


class SickBeard(object):
    """Sickbeard base class."""

    def __init__(self, config):
        """SB constructor."""
        self.config = config
        self.fork = 'auto'
