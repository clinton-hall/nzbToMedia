from __future__ import annotations

import time

import requests

import core.utils.common
from core import logger
from core.auto_process.common import ProcessResult
from core.auto_process.managers.sickbeard import SickBeard


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
            logger.error(
                f'Unable to open URL: {self.url}',
                self.sb_init.section,
            )
            return ProcessResult.failure(
                f'{self.sb_init.section}: Failed to post-process - Unable to '
                f'connect to {self.sb_init.section}',
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
            result = ProcessResult.failure(
                f'{self.sb_init.section}: Failed to post-process - Server '
                f'returned status {response.status_code}',
            )
        elif response.json()['result'] == 'success':
            result = ProcessResult.success(
                f'{self.sb_init.section}:  Successfully post-processed '
                f'{self.input_name}',
            )
        else:
            # We did not receive Success confirmation.
            result = ProcessResult.failure(
                f'{self.sb_init.section}: Failed to post-process - Returned '
                f'log from {self.sb_init.section} was not as expected.',
            )
        return result


class PyMedusaApiV2(SickBeard):
    """PyMedusa apiv2 class."""

    def __init__(self, sb_init):
        super().__init__(sb_init)

        # Check for an apikey
        # This is required with using fork = medusa-apiv2
        if not sb_init.apikey:
            logger.error(
                'For the section SickBeard `fork = medusa-apiv2` you also '
                'need to configure an `apikey`',
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
        headers = {
            'x-api-key': self.sb_init.apikey,
            'Content-type': 'application/json',
        }
        self.session.headers.update(headers)

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
            return ProcessResult.failure(
                f'{self.sb_init.section}: Unable to send postprocess request '
                f'to PyMedusa',
            )

        # Get UUID
        if response:
            try:
                jdata = response.json()
            except ValueError:
                logger.debug('No data returned from provider')
                return ProcessResult.failure('No data returned from provider')
        else:
            jdata = {}

        status = jdata.get('status', None)
        if status != 'success':
            return ProcessResult.failure()

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
