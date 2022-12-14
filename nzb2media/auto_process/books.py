from __future__ import annotations

import copy
import errno
import json
import os
import shutil
import time

import requests
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session

import nzb2media
from nzb2media import logger
from nzb2media import transcoder
from nzb2media.auto_process.common import command_complete
from nzb2media.auto_process.common import completed_download_handling
from nzb2media.auto_process.common import ProcessResult
from nzb2media.auto_process.managers.sickbeard import InitSickBeard
from nzb2media.plugins.downloaders.nzb.utils import report_nzb
from nzb2media.plugins.subtitles import import_subs
from nzb2media.plugins.subtitles import rename_subs
from nzb2media.scene_exceptions import process_all_exceptions
from nzb2media.utils.encoding import convert_to_ascii
from nzb2media.utils.network import find_download
from nzb2media.utils.identification import find_imdbid
from nzb2media.utils.common import flatten
from nzb2media.utils.files import list_media_files
from nzb2media.utils.paths import remote_dir
from nzb2media.utils.paths import remove_dir
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
    remote_path = int(cfg.get('remote_path', 0))

    # Misc

    # Begin processing
    url = nzb2media.utils.common.create_url(scheme, host, port, web_root)
    if not server_responding(url):
        logger.error('Server did not respond. Exiting', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - {section} did not respond.',
        )

    input_name, dir_name = convert_to_ascii(input_name, dir_name)

    params = {
        'apikey': apikey,
        'cmd': 'forceProcess',
        'dir': remote_dir(dir_name) if remote_path else dir_name,
    }

    logger.debug(f'Opening URL: {url} with params: {params}', section)

    try:
        r = requests.get(url, params=params, verify=False, timeout=(30, 300))
    except requests.ConnectionError:
        logger.error('Unable to open URL')
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Unable to connect to '
            f'{section}',
        )

    logger.postprocess(f'{r.text}', section)

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
    elif r.text == 'OK':
        logger.postprocess(
            f'SUCCESS: ForceProcess for {dir_name} has been started in LazyLibrarian',
            section,
        )
        return ProcessResult.success(
            f'{section}: Successfully post-processed {input_name}',
        )
    else:
        logger.error(
            f'FAILED: ForceProcess of {dir_name} has Failed in LazyLibrarian',
            section,
        )
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Returned log from {section} '
            f'was not as expected.',
        )
