from __future__ import annotations

import os
import shutil

import requests

import nzb2media
from nzb2media import logger
from nzb2media.auto_process.common import ProcessResult
from nzb2media.utils.common import flatten
from nzb2media.utils.encoding import convert_to_ascii
from nzb2media.utils.network import server_responding


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

    # Misc
    library = cfg.get('library')

    # Begin processing
    url = nzb2media.utils.common.create_url(scheme, host, port, web_root)
    if not server_responding(url):
        logger.error('Server did not respond. Exiting', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - {section} did not respond.',
        )

    input_name, dir_name = convert_to_ascii(input_name, dir_name)

    fields = input_name.split('-')

    gamez_id = fields[0].replace('[', '').replace(']', '').replace(' ', '')

    download_status = 'Downloaded' if status == 0 else 'Wanted'

    params = {
        'api_key': apikey,
        'mode': 'UPDATEREQUESTEDSTATUS',
        'db_id': gamez_id,
        'status': download_status,
    }

    logger.debug(f'Opening URL: {url}', section)

    try:
        r = requests.get(url, params=params, verify=False, timeout=(30, 300))
    except requests.ConnectionError:
        logger.error('Unable to open URL')
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Unable to connect to '
            f'{section}',
        )

    result = r.json()
    logger.postprocess(result, section)
    if library:
        logger.postprocess(f'moving files to library: {library}', section)
        try:
            shutil.move(dir_name, os.path.join(library, input_name))
        except Exception:
            logger.error(
                f'Unable to move {dir_name} to {os.path.join(library, input_name)}',
                section,
            )
            return ProcessResult.failure(
                f'{section}: Failed to post-process - Unable to move files',
            )
    else:
        logger.error(
            'No library specified to move files to. Please edit your configuration.',
            section,
        )
        return ProcessResult.failure(
            f'{section}: Failed to post-process - No library defined in '
            f'{section}',
        )

    if r.status_code not in [
        requests.codes.ok,
        requests.codes.created,
        requests.codes.accepted,
    ]:
        logger.error(f'Server returned status {r.status_code}', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Server returned status '
            f'{r.status_code}',
        )
    elif result['success']:
        logger.postprocess(
            f'SUCCESS: Status for {gamez_id} has been set to {download_status} in Gamez',
            section,
        )
        return ProcessResult.success(
            f'{section}: Successfully post-processed {input_name}',
        )
    else:
        logger.error(
            f'FAILED: Status for {gamez_id} has NOT been updated in Gamez',
            section,
        )
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Returned log from {section} '
            f'was not as expected.',
        )
