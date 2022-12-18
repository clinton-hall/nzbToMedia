from __future__ import annotations

import logging
import os
import shutil

import requests

import nzb2media
import nzb2media.utils.common
from nzb2media.auto_process.common import ProcessResult
from nzb2media.utils.encoding import convert_to_ascii
from nzb2media.utils.network import server_responding

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def process(*, section: str, dir_name: str, input_name: str = '', status: int = 0, input_category: str = '', **kwargs) -> ProcessResult:
    log.debug(f'Unused kwargs: {kwargs}')
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
    # Misc
    library = cfg.get('library')
    # Begin processing
    url = nzb2media.utils.common.create_url(scheme, host, port, web_root)
    if not server_responding(url):
        log.error('Server did not respond. Exiting')
        return ProcessResult.failure(f'{section}: Failed to post-process - {section} did not respond.')
    input_name, dir_name = convert_to_ascii(input_name, dir_name)
    fields = input_name.split('-')
    gamez_id = fields[0].replace('[', '').replace(']', '').replace(' ', '')
    download_status = 'Downloaded' if status == 0 else 'Wanted'
    params = {'api_key': apikey, 'mode': 'UPDATEREQUESTEDSTATUS', 'db_id': gamez_id, 'status': download_status}
    log.debug(f'Opening URL: {url}')
    try:
        resposne = requests.get(url, params=params, verify=False, timeout=(30, 300))
    except requests.ConnectionError:
        log.error('Unable to open URL')
        return ProcessResult.failure(f'{section}: Failed to post-process - Unable to connect to {section}')
    result = resposne.json()
    log.debug(result)
    if library:
        log.debug(f'moving files to library: {library}')
        try:
            shutil.move(dir_name, os.path.join(library, input_name))
        except Exception:
            log.error(f'Unable to move {dir_name} to {os.path.join(library, input_name)}')
            return ProcessResult.failure(f'{section}: Failed to post-process - Unable to move files')
    else:
        log.error('No library specified to move files to. Please edit your configuration.')
        return ProcessResult.failure(f'{section}: Failed to post-process - No library defined in {section}')
    if resposne.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        log.error(f'Server returned status {resposne.status_code}')
        return ProcessResult.failure(f'{section}: Failed to post-process - Server returned status {resposne.status_code}')
    if result['success']:
        log.debug(f'SUCCESS: Status for {gamez_id} has been set to {download_status} in Gamez')
        return ProcessResult.success(f'{section}: Successfully post-processed {input_name}')
    log.error(f'FAILED: Status for {gamez_id} has NOT been updated in Gamez')
    return ProcessResult.failure(f'{section}: Failed to post-process - Returned log from {section} was not as expected.')
