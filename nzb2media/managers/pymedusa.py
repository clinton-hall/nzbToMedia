from __future__ import annotations

import logging
import time

import requests

import nzb2media.utils.common
from nzb2media.auto_process.common import ProcessResult
from nzb2media.managers.sickbeard import SickBeard

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class PyMedusa(SickBeard):
    """PyMedusa class."""

    @property
    def url(self):
        route = f'{self.sb_init.web_root}/home/postprocess/processEpisode'
        return nzb2media.utils.common.create_url(
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
        return nzb2media.utils.common.create_url(
            self.sb_init.protocol,
            self.sb_init.host,
            self.sb_init.port,
            route,
        )

    def api_call(self) -> ProcessResult:
        self._process_fork_prarams()
        log.debug(f'Opening URL: {self.url} with params: {self.sb_init.fork_params}')
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
            log.error(f'Unable to open URL: {self.url}')
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
            log.error(f'Server returned status {response.status_code}')
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
            log.error(
                'For the section SickBeard `fork = medusa-apiv2` you also '
                'need to configure an `apikey`',
            )
            raise ValueError('Missing apikey for fork: medusa-apiv2')

    @property
    def url(self):
        route = f'{self.sb_init.web_root}/api/v2/postprocess'
        return nzb2media.utils.common.create_url(
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
            log.error('Unable to get postprocess identifier status')
            return False

        try:
            jdata = response.json()
        except ValueError:
            return False

        return jdata

    def api_call(self) -> ProcessResult:
        self._process_fork_prarams()
        log.debug(f'Opening URL: {self.url}')
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
            log.error('Unable to send postprocess request')
            return ProcessResult.failure(
                f'{self.sb_init.section}: Unable to send postprocess request '
                f'to PyMedusa',
            )

        # Get UUID
        if response:
            try:
                jdata = response.json()
            except ValueError:
                log.debug('No data returned from provider')
                return ProcessResult.failure('No data returned from provider')
        else:
            jdata = {}

        status = jdata.get('status', None)
        if status != 'success':
            return ProcessResult.failure()

        wait_for = int(self.sb_init.config.get('wait_for', 2))
        num = 0
        response = {}

        queue_item_identifier = jdata['queueItem']['identifier']
        url = f'{self.url}/{queue_item_identifier}'
        while num < 12:  # set up wait_for minutes to see if command completes..
            time.sleep(5 * wait_for)
            response = self._get_identifier_status(url)
            if response and response.get('success'):
                break
            if 'error' in response:
                break
            num += 1

        # Log Medusa's PP logs here.
        if response.get('output'):
            for line in response['output']:
                log.debug(line)

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
