# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import copy

import core
from core import logger
from core.auto_process.common import (
    ProcessResult,
)
from core.utils import remote_dir

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

        self.fork = ''
        self.fork_params = None
        self.fork_obj = None

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
            'medusa-apiv1': 'Medusa-api',
            'medusa-apiv2': 'Medusa-apiv2',
            'sickbeard-api': 'SickBeard-api',
            'sickgear': 'SickGear',
            'sickchill': 'SickChill',
            'stheno': 'Stheno',
        }
        _val = cfg.get('fork', 'auto')
        f1 = replace.get(_val.lower(), _val)
        try:
            self.fork = f1, core.FORKS[f1]
        except KeyError:
            self.fork = 'auto'
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

            self.fork = ['default', {}]

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

            self.fork = ['default', params]

        elif self.fork == 'auto':
            self.detect_fork()

        logger.info('{section}:{category} fork set to {fork}'.format
                    (section=self.section, category=self.input_category, fork=self.fork[0]))
        core.FORK_SET = self.fork
        self.fork, self.fork_params = self.fork[0], self.fork[1]
        # This will create the fork object, and attach to self.fork_obj.
        self._init_fork()
        return self.fork, self.fork_params

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
            self.fork = fork
            logger.info('{section}:{category} fork auto-detection successful ...'.format
                        (section=self.section, category=self.input_category))
        elif rem_params:
            logger.info('{section}:{category} fork auto-detection found custom params {params}'.format
                        (section=self.section, category=self.input_category, params=params))
            self.fork = ['custom', params]
        else:
            logger.info('{section}:{category} fork auto-detection failed'.format
                        (section=self.section, category=self.input_category))
            self.fork = list(core.FORKS.items())[list(core.FORKS.keys()).index(core.FORK_DEFAULT)]

    def _init_fork(self):
        # These need to be imported here, to prevent a circular import.
        from .pymedusa import PyMedusa, PyMedusaApiV1, PyMedusaApiV2

        mapped_forks = {
            'Medusa': PyMedusa,
            'Medusa-api': PyMedusaApiV1,
            'Medusa-apiv2': PyMedusaApiV2
        }
        logger.debug('Create object for fork {fork}'.format(fork=self.fork))
        if self.fork and mapped_forks.get(self.fork):
            # Create the fork object and pass self (SickBeardInit) to it for all the data, like Config.
            self.fork_obj = mapped_forks[self.fork](self)
        else:
            logger.info('{section}:{category} Could not create a fork object for {fork}. Probaly class not added yet.'.format(
                section=self.section, category=self.input_category, fork=self.fork)
            )


class SickBeard(object):
    """Sickbeard base class."""

    def __init__(self, sb_init):
        """SB constructor."""
        self.sb_init = sb_init
        self.session = requests.Session()

        self.failed = None
        self.status = None
        self.input_name = None
        self.dir_name = None

        self.delete_failed = int(self.sb_init.config.get('delete_failed', 0))
        self.nzb_extraction_by = self.sb_init.config.get('nzbExtractionBy', 'Downloader')
        self.process_method = self.sb_init.config.get('process_method')
        self.remote_path = int(self.sb_init.config.get('remote_path', 0))
        self.wait_for = int(self.sb_init.config.get('wait_for', 2))
        self.force = int(self.sb_init.config.get('force', 0))
        self.delete_on = int(self.sb_init.config.get('delete_on', 0))
        self.ignore_subs = int(self.sb_init.config.get('ignore_subs', 0))
        self.is_priority = int(self.sb_init.config.get('is_priority', 0))

        # get importmode, default to 'Move' for consistency with legacy
        self.import_mode = self.sb_init.config.get('importMode', 'Move')

        # Keep track of result state
        self.success = False

    def initialize(self, dir_name, input_name=None, failed=False, client_agent='manual'):
        """We need to call this explicitely because we need some variables.

        We can't pass these directly through the constructor.
        """
        self.dir_name = dir_name
        self.input_name = input_name
        self.failed = failed
        self.status = int(self.failed)
        if self.status > 0 and core.NOEXTRACTFAILED:
            self.extract = 0
        else:
            self.extract = int(self.sb_init.config.get('extract', 0))
        if client_agent == core.TORRENT_CLIENT_AGENT and core.USE_LINK == 'move-sym':
            self.process_method = 'symlink'

    def _create_url(self):
        if self.sb_init.apikey:
            return '{0}{1}:{2}{3}/api/{4}/'.format(self.sb_init.protocol, self.sb_init.host, self.sb_init.port, self.sb_init.web_root, self.sb_init.apikey)
        return '{0}{1}:{2}{3}/home/postprocess/processEpisode'.format(self.sb_init.protocol, self.sb_init.host, self.sb_init.port, self.sb_init.web_root)

    def _process_fork_prarams(self):
        # configure SB params to pass
        fork_params = self.sb_init.fork_params
        fork_params['quiet'] = 1
        fork_params['proc_type'] = 'manual'
        if self.input_name is not None:
            fork_params['nzbName'] = self.input_name

        for param in copy.copy(fork_params):
            if param == 'failed':
                if self.failed > 1:
                    self.failed = 1
                fork_params[param] = self.failed
                if 'proc_type' in fork_params:
                    del fork_params['proc_type']
                if 'type' in fork_params:
                    del fork_params['type']

            if param == 'return_data':
                fork_params[param] = 0
                if 'quiet' in fork_params:
                    del fork_params['quiet']

            if param == 'type':
                if 'type' in fork_params:  # only set if we haven't already deleted for 'failed' above.
                    fork_params[param] = 'manual'
                if 'proc_type' in fork_params:
                    del fork_params['proc_type']

            if param in ['dir_name', 'dir', 'proc_dir', 'process_directory', 'path']:
                fork_params[param] = self.dir_name
                if self.remote_path:
                    fork_params[param] = remote_dir(self.dir_name)
                # SickChill allows multiple path types. Only retunr 'path'
                if param == 'proc_dir' and 'path' in fork_params:
                    del fork_params['proc_dir']

            if param == 'process_method':
                if self.process_method:
                    fork_params[param] = self.process_method
                else:
                    del fork_params[param]

            if param in ['force', 'force_replace']:
                if self.force:
                    fork_params[param] = self.force
                else:
                    del fork_params[param]

            if param in ['delete_on', 'delete']:
                if self.delete_on:
                    fork_params[param] = self.delete_on
                else:
                    del fork_params[param]

            if param == 'ignore_subs':
                if self.ignore_subs:
                    fork_params[param] = self.ignore_subs
                else:
                    del fork_params[param]

            if param == 'is_priority':
                if self.is_priority:
                    fork_params[param] = self.is_priority
                else:
                    del fork_params[param]

            if param == 'force_next':
                fork_params[param] = 1

        # delete any unused params so we don't pass them to SB by mistake
        [fork_params.pop(k) for k, v in list(fork_params.items()) if v is None]

    def api_call(self):
        """Perform a base sickbeard api call."""
        self._process_fork_prarams()
        url = self._create_url()

        logger.debug('Opening URL: {0} with params: {1}'.format(url, self.sb_init.fork_params), self.sb_init.section)
        try:
            if not self.sb_init.apikey and self.sb_init.username and self.sb_init.password:
                # If not using the api, we need to login using user/pass first.
                login = '{0}{1}:{2}{3}/login'.format(self.sb_init.protocol, self.sb_init.host, self.sb_init.port, self.sb_init.web_root)
                login_params = {'username': self.sb_init.username, 'password': self.sb_init.password}
                r = self.session.get(login, verify=False, timeout=(30, 60))
                if r.status_code in [401, 403] and r.cookies.get('_xsrf'):
                    login_params['_xsrf'] = r.cookies.get('_xsrf')
                self.session.post(login, data=login_params, stream=True, verify=False, timeout=(30, 60))
            response = self.session.get(url, auth=(self.sb_init.username, self.sb_init.password), params=self.sb_init.fork_params, stream=True, verify=False, timeout=(30, 1800))
        except requests.ConnectionError:
            logger.error('Unable to open URL: {0}'.format(url), self.sb_init.section)
            return ProcessResult(
                message='{0}: Failed to post-process - Unable to connect to {0}'.format(self.sb_init.section),
                status_code=1,
            )

        if response.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error('Server returned status {0}'.format(response.status_code), self.sb_init.section)
            return ProcessResult(
                message='{0}: Failed to post-process - Server returned status {1}'.format(self.sb_init.section, response.status_code),
                status_code=1,
            )

        return self.process_response(response)

    def process_response(self, response):
        """Iterate over the lines returned, and log.

        :param response: Streamed Requests response object.
        This method will need to be overwritten in the forks, for alternative response handling.
        """
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                logger.postprocess('{0}'.format(line), self.sb_init.section)
                # if 'Moving file from' in line:
                #     input_name = os.path.split(line)[1]
                # if 'added to the queue' in line:
                #     queued = True
                # For the refactoring i'm only considering vanilla sickbeard, as for the base class.
                if 'Processing succeeded' in line or 'Successfully processed' in line:
                    self.success = True

        if self.success:
            return ProcessResult(
                message='{0}: Successfully post-processed {1}'.format(self.sb_init.section, self.input_name),
                status_code=0,
            )
        return ProcessResult(
            message='{0}: Failed to post-process - Returned log from {0} was not as expected.'.format(self.sb_init.section),
            status_code=1,  # We did not receive Success confirmation.
        )
