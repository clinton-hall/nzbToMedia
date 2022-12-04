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

    # Begin processing
    url = core.utils.common.create_url(scheme, host, port, web_root)
    if not server_responding(url):
        logger.error('Server did not respond. Exiting', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - {section} did not respond.'
        )

    input_name, dir_name = convert_to_ascii(input_name, dir_name)

    params = {
        'apikey': apikey,
        'cmd': 'forceProcess',
        'dir': remote_dir(dir_name) if remote_path else dir_name,
    }

    logger.debug('Opening URL: {0} with params: {1}'.format(url, params), section)

    try:
        r = requests.get(url, params=params, verify=False, timeout=(30, 300))
    except requests.ConnectionError:
        logger.error('Unable to open URL')
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Unable to connect to '
            f'{section}'
        )

    logger.postprocess('{0}'.format(r.text), section)

    if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        logger.error('Server returned status {0}'.format(r.status_code), section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Server returned status '
            f'{r.status_code}'
        )
    elif r.text == 'OK':
        logger.postprocess('SUCCESS: ForceProcess for {0} has been started in LazyLibrarian'.format(dir_name), section)
        return ProcessResult.success(
            f'{section}: Successfully post-processed {input_name}'
        )
    else:
        logger.error('FAILED: ForceProcess of {0} has Failed in LazyLibrarian'.format(dir_name), section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Returned log from {section} '
            f'was not as expected.'
        )
