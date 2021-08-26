import time

from core import logger
from core.auto_process.common import ProcessResult
from core.auto_process.managers.sickbeard import SickBeard

import requests


class PyMedusa(SickBeard):
    """PyMedusa class."""

    def __init__(self, sb_init):
        super(PyMedusa, self).__init__(sb_init)

    def _create_url(self):
        return '{0}{1}:{2}{3}/home/postprocess/processEpisode'.format(self.sb_init.protocol, self.sb_init.host, self.sb_init.port, self.sb_init.web_root)


class PyMedusaApiV1(SickBeard):
    """PyMedusa apiv1 class."""

    def __init__(self, sb_init):
        super(PyMedusaApiV1, self).__init__(sb_init)

    def _create_url(self):
        return '{0}{1}:{2}{3}/api/{4}/'.format(self.sb_init.protocol, self.sb_init.host, self.sb_init.port, self.sb_init.web_root, self.sb_init.apikey)

    def api_call(self):
        self._process_fork_prarams()
        url = self._create_url()

        logger.debug('Opening URL: {0} with params: {1}'.format(url, self.sb_init.fork_params), self.sb_init.section)
        try:
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

        if response.json()['result'] == 'success':
            return ProcessResult(
                message='{0}: Successfully post-processed {1}'.format(self.sb_init.section, self.input_name),
                status_code=0,
            )
        return ProcessResult(
            message='{0}: Failed to post-process - Returned log from {0} was not as expected.'.format(self.sb_init.section),
            status_code=1,  # We did not receive Success confirmation.
        )


class PyMedusaApiV2(SickBeard):
    """PyMedusa apiv2 class."""

    def __init__(self, sb_init):
        super(PyMedusaApiV2, self).__init__(sb_init)

        # Check for an apikey, as this is required with using fork = medusa-apiv2
        if not sb_init.apikey:
            raise Exception('For the section SickBeard `fork = medusa-apiv2` you also need to configure an `apikey`')

    def _create_url(self):
        return '{0}{1}:{2}{3}/api/v2/postprocess'.format(self.sb_init.protocol, self.sb_init.host, self.sb_init.port, self.sb_init.web_root)

    def _get_identifier_status(self, url):
        # Loop through requesting medusa for the status on the queueitem.
        try:
            response = self.session.get(url, verify=False, timeout=(30, 1800))
        except requests.ConnectionError:
            logger.error('Unable to get postprocess identifier status', self.sb_init.section)
            return False

        try:
            jdata = response.json()
        except ValueError:
            return False

        return jdata

    def api_call(self):
        self._process_fork_prarams()
        url = self._create_url()

        logger.debug('Opening URL: {0}'.format(url), self.sb_init.section)
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
            response = self.session.post(url, json=payload, verify=False, timeout=(30, 1800))
        except requests.ConnectionError:
            logger.error('Unable to send postprocess request', self.sb_init.section)
            return ProcessResult(
                message='{0}: Unable to send postprocess request to PyMedusa',
                status_code=1,
            )

        # Get UUID
        if response:
            try:
                jdata = response.json()
            except ValueError:
                logger.debug('No data returned from provider')
                return False

        if not jdata.get('status') or not jdata['status'] == 'success':
            return False

        queueitem_identifier = jdata['queueItem']['identifier']

        wait_for = int(self.sb_init.config.get('wait_for', 2))
        n = 0
        response = {}
        url = '{0}/{1}'.format(url, queueitem_identifier)
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
                logger.postprocess('{0}'.format(line), self.sb_init.section)

        # For now this will most likely always be True. But in the future we could return an exit state
        # for when the PP in medusa didn't yield an expected result.
        if response.get('success'):
            return ProcessResult(
                message='{0}: Successfully post-processed {1}'.format(self.sb_init.section, self.input_name),
                status_code=0,
            )
        return ProcessResult(
            message='{0}: Failed to post-process - Returned log from {0} was not as expected.'.format(self.sb_init.section),
            status_code=1,  # We did not receive Success confirmation.
        )
