from __future__ import annotations

import copy

import requests
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session

import core
from core import logger
from core.auto_process.common import (
    ProcessResult,
)
from core.utils import remote_dir


class InitSickBeard:
    """SickBeard init class.

    Used to determine which SickBeard fork object to initialize.
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
        if core.FORK_SET:
            # keep using determined fork for multiple (manual) post-processing
            logger.info(
                f'{self.section}:{self.input_category} fork already set to '
                f'{core.FORK_SET[0]}',
            )
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
            logger.info(f'Attempting to verify {self.input_category} fork')
            url = core.utils.common.create_url(
                scheme=protocol,
                host=self.host,
                port=self.port,
                path=f'{self.web_root}/api/rootfolder',
            )
            headers = {'X-Api-Key': self.apikey}
            try:
                r = requests.get(
                    url,
                    headers=headers,
                    stream=True,
                    verify=False,
                )
            except requests.ConnectionError:
                logger.warning(
                    f'Could not connect to {self.section}:'
                    f'{self.input_category} to verify fork!',
                )

            if not r.ok:
                logger.warning(
                    f'Connection to {self.section}:{self.input_category} '
                    f'failed! Check your configuration',
                )

            self.fork = ['default', {}]

        elif self.section == 'SiCKRAGE':
            logger.info(f'Attempting to verify {self.input_category} fork')

            if self.api_version >= 2:
                url = core.utils.common.create_url(
                    scheme=protocol,
                    host=self.host,
                    port=self.port,
                    path=f'{self.web_root}/api/v{self.api_version}/ping',
                )
                api_params = {}
            else:
                api_version = f'v{self.api_version}'
                url = core.utils.common.create_url(
                    scheme=protocol,
                    host=self.host,
                    port=self.port,
                    path=f'{self.web_root}/api/{api_version}/{self.apikey}/',
                )
                api_params = {'cmd': 'postprocess', 'help': '1'}

            try:
                if (
                    self.api_version >= 2
                    and self.sso_username
                    and self.sso_password
                ):
                    oauth = OAuth2Session(
                        client=LegacyApplicationClient(
                            client_id=core.SICKRAGE_OAUTH_CLIENT_ID,
                        ),
                    )
                    oauth_token = oauth.fetch_token(
                        client_id=core.SICKRAGE_OAUTH_CLIENT_ID,
                        token_url=core.SICKRAGE_OAUTH_TOKEN_URL,
                        username=self.sso_username,
                        password=self.sso_password,
                    )
                    token = oauth_token['access_token']
                    r = requests.get(
                        url,
                        headers={f'Authorization': f'Bearer {token}'},
                        stream=True,
                        verify=False,
                    )
                else:
                    r = requests.get(
                        url,
                        params=api_params,
                        stream=True,
                        verify=False,
                    )

                if not r.ok:
                    logger.warning(
                        f'Connection to {self.section}:{self.input_category} '
                        f'failed! Check your configuration',
                    )
            except requests.ConnectionError:
                logger.warning(
                    f'Could not connect to {self.section}:'
                    f'{self.input_category} to verify API version!',
                )

            params = {
                'path': None,
                'failed': None,
                'process_method': None,
                'force_replace': None,
                'return_data': None,
                'type': None,
                'delete': None,
                'force_next': None,
                'is_priority': None,
            }

            self.fork = ['default', params]

        elif self.fork == 'auto':
            self.detect_fork()

        logger.info(
            f'{self.section}:{self.input_category} fork set to {self.fork[0]}',
        )
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
            logger.debug(f'Response received: {json_data}')
            raise
        else:
            if isinstance(json_data, str):
                return rem_params, False
            json_data = json_data.get('data', json_data)

        try:
            optional_parameters = json_data['optionalParameters'].keys()
            # Find excess parameters
            excess_parameters = set(params).difference(optional_parameters)
            excess_parameters.remove('cmd')  # Don't remove cmd from api params
            logger.debug(
                f'Removing excess parameters: ' f'{sorted(excess_parameters)}',
            )
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
        logger.info(f'Attempting to auto-detect {self.input_category} fork')
        # Define the order to test.
        # Default must be first since default fork doesn't reject parameters.
        # Then in order of most unique parameters.

        if self.apikey:
            url = core.utils.common.create_url(
                scheme=self.protocol,
                host=self.host,
                port=self.port,
                path=f'{self.web_root}/api/{self.apikey}/',
            )
            api_params = {'cmd': 'sg.postprocess', 'help': '1'}
        else:
            url = core.utils.common.create_url(
                scheme=self.protocol,
                host=self.host,
                port=self.port,
                path=f'{self.web_root}/home/postprocess',
            )
            api_params = {}

        # attempting to auto-detect fork
        try:
            s = requests.Session()

            if not self.apikey and self.username and self.password:
                login = core.utils.common.create_url(
                    scheme=self.protocol,
                    host=self.host,
                    port=self.port,
                    path=f'{self.web_root}/login',
                )
                login_params = {
                    'username': self.username,
                    'password': self.password,
                }
                r = s.get(login, verify=False, timeout=(30, 60))
                if r.status_code in [401, 403] and r.cookies.get('_xsrf'):
                    login_params['_xsrf'] = r.cookies.get('_xsrf')
                s.post(login, data=login_params, stream=True, verify=False)
            r = s.get(
                url,
                auth=(self.username, self.password),
                params=api_params,
                verify=False,
            )
        except requests.ConnectionError:
            logger.info(
                f'Could not connect to {self.section}:{self.input_category} '
                f'to perform auto-fork detection!',
            )
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
                            r = s.get(
                                url,
                                auth=(self.username, self.password),
                                params=api_params,
                                verify=False,
                            )
                        else:
                            r = s.get(url, params=api_params, verify=False)
                    except requests.ConnectionError:
                        logger.info(
                            f'Could not connect to {self.section}:'
                            f'{self.input_category} to perform auto-fork '
                            f'detection!',
                        )
                    rem_params, found = self._api_check(r, params, rem_params)
                    params['cmd'] = 'postprocess'
            else:
                # Find excess parameters
                rem_params.extend(
                    param
                    for param in params
                    if f'name="{param}"' not in r.text
                )

            # Remove excess params
            for param in rem_params:
                params.pop(param)

            for fork in sorted(core.FORKS, reverse=False):
                if params == fork[1]:
                    detected = True
                    break

        if detected:
            self.fork = fork
            logger.info(
                f'{self.section}:{self.input_category} fork auto-detection '
                f'successful ...',
            )
        elif rem_params:
            logger.info(
                f'{self.section}:{self.input_category} fork auto-detection '
                f'found custom params {params}',
            )
            self.fork = ['custom', params]
        else:
            logger.info(
                f'{self.section}:{self.input_category} fork auto-detection '
                f'failed',
            )
            self.fork = list(core.FORKS.items())[
                list(core.FORKS.keys()).index(core.FORK_DEFAULT)
            ]

    def _init_fork(self):
        # These need to be imported here, to prevent a circular import.
        from .pymedusa import PyMedusa, PyMedusaApiV1, PyMedusaApiV2

        mapped_forks = {
            'Medusa': PyMedusa,
            'Medusa-api': PyMedusaApiV1,
            'Medusa-apiv2': PyMedusaApiV2,
        }
        logger.debug(f'Create object for fork {self.fork}')
        if self.fork and mapped_forks.get(self.fork):
            # Create the fork object and pass self (SickBeardInit) to it for all the data, like Config.
            self.fork_obj = mapped_forks[self.fork](self)
        else:
            logger.info(
                f'{self.section}:{self.input_category} Could not create a '
                f'fork object for {self.fork}. Probaly class not added yet.',
            )


class SickBeard:
    """Sickbeard base class."""

    sb_init: InitSickBeard

    def __init__(self, sb_init):
        """SB constructor."""
        self.sb_init = sb_init
        self.session = requests.Session()

        self.failed = None
        self.status = None
        self.input_name = None
        self.dir_name = None

        self.delete_failed = int(self.sb_init.config.get('delete_failed', 0))
        self.nzb_extraction_by = self.sb_init.config.get(
            'nzbExtractionBy', 'Downloader',
        )
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

    def initialize(
        self,
        dir_name,
        input_name=None,
        failed=False,
        client_agent='manual',
    ):
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
        if (
            client_agent == core.TORRENT_CLIENT_AGENT
            and core.USE_LINK == 'move-sym'
        ):
            self.process_method = 'symlink'

    @property
    def url(self) -> str:
        if self.sb_init.apikey:
            route = f'{self.sb_init.web_root}/api/{self.sb_init.apikey}/'
        else:
            route = f'{self.sb_init.web_root}/home/postprocess/processEpisode'
        return core.utils.common.create_url(
            scheme=self.sb_init.protocol,
            host=self.sb_init.host,
            port=self.sb_init.port,
            path=route,
        )

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
                if 'type' in fork_params:
                    # Set if we haven't already deleted for 'failed' above.
                    fork_params[param] = 'manual'
                if 'proc_type' in fork_params:
                    del fork_params['proc_type']

            if param in [
                'dir_name',
                'dir',
                'proc_dir',
                'process_directory',
                'path',
            ]:
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

    def api_call(self) -> ProcessResult:
        """Perform a base sickbeard api call."""
        self._process_fork_prarams()
        logger.debug(
            f'Opening URL: {self.url} with params: {self.sb_init.fork_params}',
            self.sb_init.section,
        )
        try:
            if (
                not self.sb_init.apikey
                and self.sb_init.username
                and self.sb_init.password
            ):
                # If not using the api, we need to login using user/pass first.
                route = f'{self.sb_init.web_root}/login'
                login = core.utils.common.create_url(
                    self.sb_init.protocol,
                    self.sb_init.host,
                    self.sb_init.port,
                    route,
                )
                login_params = {
                    'username': self.sb_init.username,
                    'password': self.sb_init.password,
                }
                r = self.session.get(login, verify=False, timeout=(30, 60))
                if r.status_code in [401, 403] and r.cookies.get('_xsrf'):
                    login_params['_xsrf'] = r.cookies.get('_xsrf')
                self.session.post(
                    login,
                    data=login_params,
                    stream=True,
                    verify=False,
                    timeout=(30, 60),
                )
            response = self.session.get(
                self.url,
                auth=(self.sb_init.username, self.sb_init.password),
                params=self.sb_init.fork_params,
                stream=True,
                verify=False,
                timeout=(30, 1800),
            )
        except requests.ConnectionError:
            logger.error(
                f'Unable to open URL: {self.url}', self.sb_init.section,
            )
            result = ProcessResult.failure(
                f'{self.sb_init.section}: Failed to post-process - Unable to '
                f'connect to {self.sb_init.section}',
            )
        else:
            successful_statuses = [
                requests.codes.ok,
                requests.codes.created,
                requests.codes.accepted,
            ]
            if response.status_code not in successful_statuses:
                logger.error(
                    f'Server returned status {response.status_code}',
                    self.sb_init.section,
                )
                result = ProcessResult.failure(
                    f'{self.sb_init.section}: Failed to post-process - Server '
                    f'returned status {response.status_code}',
                )
            else:
                result = self.process_response(response)
        return result

    def process_response(self, response: requests.Response) -> ProcessResult:
        """Iterate over the lines returned, and log.

        :param response: Streamed Requests response object.
        This method will need to be overwritten in the forks, for alternative response handling.
        """
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                logger.postprocess(line, self.sb_init.section)
                # if 'Moving file from' in line:
                #     input_name = os.path.split(line)[1]
                # if 'added to the queue' in line:
                #     queued = True
                # For the refactoring i'm only considering vanilla sickbeard,
                # as for the base class.
                if (
                    'Processing succeeded' in line
                    or 'Successfully processed' in line
                ):
                    self.success = True

        if self.success:
            result = ProcessResult.success(
                f'{self.sb_init.section}: Successfully post-processed '
                f'{self.input_name}',
            )
        else:
            # We did not receive Success confirmation.
            result = ProcessResult.failure(
                f'{self.sb_init.section}: Failed to post-process - Returned '
                f'log from {self.sb_init.section} was not as expected.',
            )
        return result
