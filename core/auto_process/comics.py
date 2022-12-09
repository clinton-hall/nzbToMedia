import copy
import errno
import json
import os
import shutil
import time

import requests
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session

import core
from core import logger, transcoder
from core.auto_process.common import (
    ProcessResult,
    command_complete,
    completed_download_handling,
)
from core.auto_process.managers.sickbeard import InitSickBeard
from core.plugins.downloaders.nzb.utils import report_nzb
from core.plugins.subtitles import import_subs, rename_subs
from core.scene_exceptions import process_all_exceptions
from core.utils import (
    convert_to_ascii,
    find_download,
    find_imdbid,
    flatten,
    list_media_files,
    remote_dir,
    remove_dir,
    server_responding,
)


requests.packages.urllib3.disable_warnings()


def process(
    *,
    section: str,
    dir_name: str,
    input_name: str = '',
    status: int = 0,
    failed: bool = False,
    client_agent: str = 'manual',
    download_id: str = '',
    input_category: str = '',
    failure_link: str = '',
) -> ProcessResult:
    # Get configuration
    cfg = core.CFG[section][input_category]

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
    apc_version = '2.04'
    comicrn_version = '1.01'

    # Begin processing
    url = core.utils.common.create_url(scheme, host, port, web_root)
    if not server_responding(url):
        logger.error('Server did not respond. Exiting', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - {section} did not respond.'
        )

    input_name, dir_name = convert_to_ascii(input_name, dir_name)
    clean_name, ext = os.path.splitext(input_name)
    if len(ext) == 4:  # we assume this was a standard extension.
        input_name = clean_name

    params = {
        'cmd': 'forceProcess',
        'apikey': apikey,
        'nzb_folder': remote_dir(dir_name) if remote_path else dir_name,
    }

    if input_name is not None:
        params['nzb_name'] = input_name
    params['failed'] = int(status)
    params['apc_version'] = apc_version
    params['comicrn_version'] = comicrn_version

    success = False

    logger.debug(f'Opening URL: {url}', section)
    try:
        r = requests.post(url, params=params, stream=True, verify=False, timeout=(30, 300))
    except requests.ConnectionError:
        logger.error('Unable to open URL', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Unable to connect to '
            f'{section}'
        )
    if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        logger.error(f'Server returned status {r.status_code}', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Server returned status '
            f'{r.status_code}'
        )

    result = r.text
    if not type(result) == list:
        result = result.split('\n')
    for line in result:
        if line:
            logger.postprocess(line, section)
        if 'Post Processing SUCCESSFUL' in line:
            success = True

    if success:
        logger.postprocess('SUCCESS: This issue has been processed successfully', section)
        return ProcessResult.success(
            f'{section}: Successfully post-processed {input_name}'
        )
    else:
        logger.warning('The issue does not appear to have successfully processed. Please check your Logs', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Returned log from '
            f'{section} was not as expected.'
        )
