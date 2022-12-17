from __future__ import annotations

import logging
import typing

import requests

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ProcessResult(typing.NamedTuple):
    status_code: int
    message: str

    def __bool__(self) -> bool:
        return not bool(self.status_code)

    def __str__(self) -> str:
        status = 'succeeded' if bool(self) else 'failed'
        return f'Processing {self.message}: {status}'

    def __repr__(self) -> str:
        return f'<ProcessResult {self.status_code}: {self.message}>'

    @classmethod
    def failure(cls, message: str = 'Failed'):
        return cls(1, message)

    @classmethod
    def success(cls, message: str = 'Success'):
        return cls(0, message)


def command_complete(url, params, headers, section):
    try:
        r = requests.get(
            url,
            params=params,
            headers=headers,
            stream=True,
            verify=False,
            timeout=(30, 60),
        )
    except requests.ConnectionError:
        log.error(f'Unable to open URL: {url}')
        return None
    if r.status_code not in [
        requests.codes.ok,
        requests.codes.created,
        requests.codes.accepted,
    ]:
        log.error(f'Server returned status {r.status_code}')
        return None
    else:
        try:
            return r.json()['status']
        except (ValueError, KeyError):
            # ValueError catches simplejson's JSONDecodeError and
            # json's ValueError
            log.error(f'{section} did not return expected json data.')
            return None


def completed_download_handling(url2, headers, section='MAIN'):
    try:
        r = requests.get(
            url2,
            params={},
            headers=headers,
            stream=True,
            verify=False,
            timeout=(30, 60),
        )
    except requests.ConnectionError:
        log.error(f'Unable to open URL: {url2}')
        return False
    if r.status_code not in [
        requests.codes.ok,
        requests.codes.created,
        requests.codes.accepted,
    ]:
        log.error(f'Server returned status {r.status_code}')
        return False
    else:
        try:
            return r.json().get('enableCompletedDownloadHandling', False)
        except ValueError:
            # ValueError catches simplejson's JSONDecodeError and json's ValueError
            return False
