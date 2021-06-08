from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import requests

from core import logger


class ProcessResult(object):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code

    def __iter__(self):
        return self.status_code, self.message

    def __bool__(self):
        return not bool(self.status_code)

    def __str__(self):
        return 'Processing {0}: {1}'.format(
            'succeeded' if bool(self) else 'failed',
            self.message,
        )

    def __repr__(self):
        return '<ProcessResult {0}: {1}>'.format(
            self.status_code,
            self.message,
        )


def command_complete(url, params, headers, section):
    try:
        r = requests.get(url, params=params, headers=headers, stream=True, verify=False, timeout=(30, 60))
    except requests.ConnectionError:
        logger.error('Unable to open URL: {0}'.format(url), section)
        return None
    if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        logger.error('Server returned status {0}'.format(r.status_code), section)
        return None
    else:
        try:
            return r.json()['status']
        except (ValueError, KeyError):
            # ValueError catches simplejson's JSONDecodeError and json's ValueError
            logger.error('{0} did not return expected json data.'.format(section), section)
            return None


def completed_download_handling(url2, headers, section='MAIN'):
    try:
        r = requests.get(url2, params={}, headers=headers, stream=True, verify=False, timeout=(30, 60))
    except requests.ConnectionError:
        logger.error('Unable to open URL: {0}'.format(url2), section)
        return False
    if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        logger.error('Server returned status {0}'.format(r.status_code), section)
        return False
    else:
        try:
            return r.json().get('enableCompletedDownloadHandling', False)
        except ValueError:
            # ValueError catches simplejson's JSONDecodeError and json's ValueError
            return False
