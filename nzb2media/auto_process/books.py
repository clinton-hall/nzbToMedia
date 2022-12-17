from __future__ import annotations

import logging

import requests

import nzb2media
from nzb2media.auto_process.common import ProcessResult
from nzb2media.utils.common import flatten
from nzb2media.utils.encoding import convert_to_ascii
from nzb2media.utils.network import server_responding
from nzb2media.utils.paths import remote_dir

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def process(
    *,
    section: str,
    dir_name: str,
    input_name: str = '',
    status: int = 0,
    client_agent: str = 'manual',
    download_id: str = '',
    input_category: str = '',
    failure_link: str = '',
) -> ProcessResult:
    # Get configuration
    if nzb2media.CFG is None:
        raise RuntimeError('Configuration not loaded.')
    cfg = nzb2media.CFG[section][input_category]

    # Base URL
    ssl = int(cfg.get('ssl', 0))
    scheme = 'https' if ssl else 'http'
    host = cfg['host']
    port = cfg['port']
    web_root = cfg.get('web_root', '')

    # Authentication
    apikey = cfg.get('apikey', '')

    # Params
    remote_path = int(cfg.get('remote_path', 0))

    # Misc

    # Begin processing
    url = nzb2media.utils.common.create_url(scheme, host, port, web_root)
    if not server_responding(url):
        log.error('Server did not respond. Exiting')
        return ProcessResult.failure(
            f'{section}: Failed to post-process - {section} did not respond.',
        )

    input_name, dir_name = convert_to_ascii(input_name, dir_name)

    params = {
        'apikey': apikey,
        'cmd': 'forceProcess',
        'dir': remote_dir(dir_name) if remote_path else dir_name,
    }

    log.debug(f'Opening URL: {url} with params: {params}')

    try:
        response = requests.get(url, params=params, verify=False, timeout=(30, 300))
    except requests.ConnectionError:
        log.error('Unable to open URL')
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Unable to connect to '
            f'{section}',
        )

    log.debug(response.text)

    if response.status_code not in [
        requests.codes.ok,
        requests.codes.created,
        requests.codes.accepted,
    ]:
        log.error(f'Server returned status {response.status_code}')
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Server returned status '
            f'{response.status_code}',
        )
    elif response.text == 'OK':
        log.debug(
            f'SUCCESS: ForceProcess for {dir_name} has been started in LazyLibrarian',
        )
        return ProcessResult.success(
            f'{section}: Successfully post-processed {input_name}',
        )
    else:
        log.error(
            f'FAILED: ForceProcess of {dir_name} has Failed in LazyLibrarian',
        )
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Returned log from {section} '
            f'was not as expected.',
        )
