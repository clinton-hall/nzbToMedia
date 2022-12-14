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
    delete_failed = int(cfg.get('delete_failed', 0))
    remote_path = int(cfg.get('remote_path', 0))
    wait_for = int(cfg.get('wait_for', 2))

    # Misc
    if status > 0 and nzb2media.NOEXTRACTFAILED:
        extract = 0
    else:
        extract = int(cfg.get('extract', 0))

    # Begin processing
    route = f'{web_root}/api/v1' if section == 'Lidarr' else f'{web_root}/api'
    url = nzb2media.utils.common.create_url(scheme, host, port, route)
    if not server_responding(url):
        logger.error('Server did not respond. Exiting', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - {section} did not respond.',
        )

    if not os.path.isdir(dir_name) and os.path.isfile(
        dir_name,
    ):  # If the input directory is a file, assume single file download and split dir/name.
        dir_name = os.path.split(os.path.normpath(dir_name))[0]

    specific_path = os.path.join(dir_name, str(input_name))
    clean_name = os.path.splitext(specific_path)
    if clean_name[1] == '.nzb':
        specific_path = clean_name[0]
    if os.path.isdir(specific_path):
        dir_name = specific_path

    process_all_exceptions(input_name, dir_name)
    input_name, dir_name = convert_to_ascii(input_name, dir_name)

    if (
        not list_media_files(
            dir_name, media=False, audio=True, meta=False, archives=False,
        )
        and list_media_files(
            dir_name, media=False, audio=False, meta=False, archives=True,
        )
        and extract
    ):
        logger.debug(
            f'Checking for archives to extract in directory: {dir_name}',
        )
        nzb2media.extract_files(dir_name)
        input_name, dir_name = convert_to_ascii(input_name, dir_name)

    # if listMediaFiles(dir_name, media=False, audio=True, meta=False, archives=False) and status:
    #     logger.info('Status shown as failed from Downloader, but valid video files found. Setting as successful.', section)
    #     status = 0

    if status == 0 and section == 'HeadPhones':

        params = {
            'apikey': apikey,
            'cmd': 'forceProcess',
            'dir': remote_dir(dir_name) if remote_path else dir_name,
        }

        res = force_process(
            params, url, apikey, input_name, dir_name, section, wait_for,
        )
        if res.status_code in [0, 1]:
            return res

        params = {
            'apikey': apikey,
            'cmd': 'forceProcess',
            'dir': os.path.split(remote_dir(dir_name))[0]
            if remote_path
            else os.path.split(dir_name)[0],
        }

        res = force_process(
            params, url, apikey, input_name, dir_name, section, wait_for,
        )
        if res.status_code in [0, 1]:
            return res

        # The status hasn't changed. uTorrent can resume seeding now.
        logger.warning(
            f'The music album does not appear to have changed status after {wait_for} minutes. Please check your Logs',
            section,
        )
        return ProcessResult.failure(
            f'{section}: Failed to post-process - No change in wanted status',
        )

    elif status == 0 and section == 'Lidarr':
        route = f'{web_root}/api/v1/command'
        url = nzb2media.utils.common.create_url(scheme, host, port, route)
        headers = {'X-Api-Key': apikey}
        if remote_path:
            logger.debug(f'remote_path: {remote_dir(dir_name)}', section)
            data = {'name': 'Rename', 'path': remote_dir(dir_name)}
        else:
            logger.debug(f'path: {dir_name}', section)
            data = {'name': 'Rename', 'path': dir_name}
        try:
            logger.debug(f'Opening URL: {url} with data: {data}', section)
            r = requests.post(
                url,
                data=json.dumps(data),
                headers=headers,
                stream=True,
                verify=False,
                timeout=(30, 1800),
            )
        except requests.ConnectionError:
            logger.error(f'Unable to open URL: {url}', section)
            return ProcessResult.failure(
                f'{section}: Failed to post-process - Unable to connect to '
                f'{section}',
            )

        try:
            res = r.json()
            scan_id = int(res['id'])
            logger.debug(f'Scan started with id: {scan_id}', section)
        except Exception as e:
            logger.warning(f'No scan id was returned due to: {e}', section)
            return ProcessResult.failure(
                f'{section}: Failed to post-process - Unable to start scan',
            )

        n = 0
        params = {}
        url = f'{url}/{scan_id}'
        while n < 6:  # set up wait_for minutes to see if command completes..
            time.sleep(10 * wait_for)
            command_status = command_complete(url, params, headers, section)
            if command_status and command_status in ['completed', 'failed']:
                break
            n += 1
        if command_status:
            logger.debug(
                f'The Scan command return status: {command_status}', section,
            )
        if not os.path.exists(dir_name):
            logger.debug(
                f'The directory {dir_name} has been removed. Renaming was successful.',
                section,
            )
            return ProcessResult.success(
                f'{section}: Successfully post-processed {input_name}',
            )
        elif command_status and command_status in ['completed']:
            logger.debug(
                'The Scan command has completed successfully. Renaming was successful.',
                section,
            )
            return ProcessResult.success(
                f'{section}: Successfully post-processed {input_name}',
            )
        elif command_status and command_status in ['failed']:
            logger.debug(
                'The Scan command has failed. Renaming was not successful.',
                section,
            )
            # return ProcessResult.failure(
            #     f'{section}: Failed to post-process {input_name}'
            # )
        else:
            logger.debug(
                f'The Scan command did not return status completed. Passing back to {section} to attempt complete download handling.',
                section,
            )
            return ProcessResult(
                message=f'{section}: Passing back to {section} to attempt '
                f'Complete Download Handling',
                status_code=status,
            )

    else:
        if section == 'Lidarr':
            logger.postprocess(
                f'FAILED: The download failed. Sending failed download to {section} for CDH processing',
                section,
            )
            # Return as failed to flag this in the downloader.
            return ProcessResult.failure(
                f'{section}: Download Failed. Sending back to {section}',
            )
        else:
            logger.warning('FAILED DOWNLOAD DETECTED', section)
            if (
                delete_failed
                and os.path.isdir(dir_name)
                and not os.path.dirname(dir_name) == dir_name
            ):
                logger.postprocess(
                    f'Deleting failed files and folder {dir_name}', section,
                )
                remove_dir(dir_name)
            # Return as failed to flag this in the downloader.
            return ProcessResult.failure(
                f'{section}: Failed to post-process. {section} does not '
                f'support failed downloads',
            )

    return ProcessResult.failure()


def get_status(url, apikey, dir_name):
    logger.debug(
        f'Attempting to get current status for release:{os.path.basename(dir_name)}',
    )

    params = {
        'apikey': apikey,
        'cmd': 'getHistory',
    }

    logger.debug(f'Opening URL: {url} with PARAMS: {params}')

    try:
        r = requests.get(url, params=params, verify=False, timeout=(30, 120))
    except requests.RequestException:
        logger.error('Unable to open URL')
        return None

    try:
        result = r.json()
    except ValueError:
        # ValueError catches simplejson's JSONDecodeError and json's ValueError
        return None

    for album in result:
        if os.path.basename(dir_name) == album['FolderName']:
            return album['Status'].lower()


def force_process(
    params, url, apikey, input_name, dir_name, section, wait_for,
):
    release_status = get_status(url, apikey, dir_name)
    if not release_status:
        logger.error(
            f'Could not find a status for {input_name}, is it in the wanted list ?',
            section,
        )

    logger.debug(f'Opening URL: {url} with PARAMS: {params}', section)

    try:
        r = requests.get(url, params=params, verify=False, timeout=(30, 300))
    except requests.ConnectionError:
        logger.error(f'Unable to open URL {url}', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Unable to connect to '
            f'{section}',
        )

    logger.debug(f'Result: {r.text}', section)

    if r.status_code not in [
        requests.codes.ok,
        requests.codes.created,
        requests.codes.accepted,
    ]:
        logger.error(f'Server returned status {r.status_code}', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Server returned status {r.status_code}',
        )
    elif r.text == 'OK':
        logger.postprocess(
            f'SUCCESS: Post-Processing started for {input_name} in folder {dir_name} ...',
            section,
        )
    else:
        logger.error(
            f'FAILED: Post-Processing has NOT started for {input_name} in folder {dir_name}. exiting!',
            section,
        )
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Returned log from {section} '
            f'was not as expected.',
        )

    # we will now wait for this album to be processed before returning to TorrentToMedia and unpausing.
    timeout = time.time() + 60 * wait_for
    while time.time() < timeout:
        current_status = get_status(url, apikey, dir_name)
        if (
            current_status is not None and current_status != release_status
        ):  # Something has changed. CPS must have processed this movie.
            logger.postprocess(
                f'SUCCESS: This release is now marked as status [{current_status}]',
                section,
            )
            return ProcessResult.success(
                f'{section}: Successfully post-processed {input_name}',
            )
        if not os.path.isdir(dir_name):
            logger.postprocess(
                f'SUCCESS: The input directory {dir_name} has been removed Processing must have finished.',
                section,
            )
            return ProcessResult.success(
                f'{section}: Successfully post-processed {input_name}',
            )
        time.sleep(10 * wait_for)
    # The status hasn't changed.
    return ProcessResult(
        message='no change',
        status_code=2,
    )
