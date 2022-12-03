import time

import core.utils.common
from core import logger
from core.auto_process.common import ProcessResult
from core.auto_process.managers.sickbeard import SickBeard

import requests


class PyMedusa(SickBeard):
    """PyMedusa class."""

    @property
    def url(self):
        route = f'{self.sb_init.web_root}/home/postprocess/processEpisode'
        return core.utils.common.create_url(
            self.sb_init.protocol,
            self.sb_init.host,
            self.sb_init.port,
            route,
        )


class PyMedusaApiV1(SickBeard):
    """PyMedusa apiv1 class."""

    @property
    def url(self) -> str:
        route = f'{self.sb_init.web_root}/api/{self.sb_init.apikey}/'
        return core.utils.common.create_url(
            self.sb_init.protocol,
            self.sb_init.host,
            self.sb_init.port,
            route,
        )

    def api_call(self) -> ProcessResult:
        self._process_fork_prarams()
        logger.debug(
            f'Opening URL: {self.url} with params: {self.sb_init.fork_params}',
            self.sb_init.section,
        )
        try:
            response = self.session.get(
                self.url,
                auth=(self.sb_init.username, self.sb_init.password),
                params=self.sb_init.fork_params,
                stream=True,
                verify=False,
                timeout=(30, 1800),
            )
        except requests.ConnectionError:
            logger.error(f'Unable to open URL: {self.url}', self.sb_init.section)
            return ProcessResult(
                message=f'{self.sb_init.section}: Failed to post-process - '
                        f'Unable to connect to {self.sb_init.section}',
                status_code=1,
            )

        successful_status_codes = [
            requests.codes.ok,
            requests.codes.created,
            requests.codes.accepted,
        ]
        if response.status_code not in successful_status_codes:
            logger.error(
                f'Server returned status {response.status_code}',
                self.sb_init.section,
            )
            return ProcessResult(
                message=f'{self.sb_init.section}: Failed to post-process - '
                        f'Server returned status {response.status_code}',
                status_code=1,
            )

        if response.json()['result'] == 'success':
            return ProcessResult(
                message=f'{self.sb_init.section}: '
                        f'Successfully post-processed {self.input_name}',
                status_code=0,
            )
        return ProcessResult(
            message=f'{self.sb_init.section}: Failed to post-process - '
                    f'Returned log from {self.sb_init.section} was not as '
                    f'expected.',
            status_code=1,  # We did not receive Success confirmation.
        )


class PyMedusaApiV2(SickBeard):
    """PyMedusa apiv2 class."""

    def __init__(self, sb_init):
        super().__init__(sb_init)

        # Check for an apikey
        # This is required with using fork = medusa-apiv2
        if not sb_init.apikey:
            logger.error(
                'For the section SickBeard `fork = medusa-apiv2` you also '
                'need to configure an `apikey`'
            )
            raise ValueError('Missing apikey for fork: medusa-apiv2')

    @property
    def url(self):
        route = f'{self.sb_init.web_root}/api/v2/postprocess'
        return core.utils.common.create_url(
            self.sb_init.protocol,
            self.sb_init.host,
            self.sb_init.port,
            route,
        )

    def _get_identifier_status(self, url):
        # Loop through requesting medusa for the status on the queueitem.
        try:
            response = self.session.get(url, verify=False, timeout=(30, 1800))
        except requests.ConnectionError:
            logger.error(
                'Unable to get postprocess identifier status',
                self.sb_init.section,
            )
            return False

        try:
            jdata = response.json()
        except ValueError:
            return False

        return jdata

    def api_call(self) -> ProcessResult:
        self._process_fork_prarams()
        logger.debug(f'Opening URL: {self.url}', self.sb_init.section)
        payload = self.sb_init.fork_params
        payload['resource'] = self.sb_init.fork_params['nzbName']
        del payload['nzbName']

        # Update the session with the x-api-key
        self.session.headers.update({
            'x-api-key': self.sb_init.apikey,
            'Content-type': 'application/json'
        })

        # Send postprocess request
        try:
            response = self.session.post(
                self.url,
                json=payload,
                verify=False,
                timeout=(30, 1800),
            )
        except requests.ConnectionError:
            logger.error(
                'Unable to send postprocess request',
                self.sb_init.section,
            )
            return ProcessResult(
                message=f'{self.sb_init.section}: Unable to send postprocess '
                        f'request to PyMedusa',
                status_code=1,
            )

        # Get UUID
        if response:
            try:
                jdata = response.json()
            except ValueError:
                logger.debug('No data returned from provider')
                return False
        else:
            jdata = {}

        status = jdata.get('status', None)
        if status != 'success':
            return False

        wait_for = int(self.sb_init.config.get('wait_for', 2))
        n = 0
        response = {}

        queue_item_identifier = jdata['queueItem']['identifier']
        url = f'{self.url}/{queue_item_identifier}'
        while n < 12:  # set up wait_for minutes to see if command completes..
            time.sleep(5 * wait_for)
            response = self._get_identifier_status(url)
            if response and response.get('success'):
                break
            if 'error' in response:
                break
            n += 1

        # Log Medusa's PP logs here.
        if response.get('output'):
            for line in response['output']:
                logger.postprocess(line, self.sb_init.section)

        # For now this will most likely always be True.
        # In the future we could return an exit state for when the PP in
        # medusa didn't yield an expected result.
        if response.get('success'):
            return ProcessResult(
                message=f'{self.sb_init.section}: '
                        f'Successfully post-processed {self.input_name}',
                status_code=0,
            )
        return ProcessResult(
            message=f'{self.sb_init.section}: Failed to post-process - '
                    f'Returned log from {self.sb_init.section} was not '
                    f'as expected.',
            status_code=1,  # We did not receive Success confirmation.
        )
