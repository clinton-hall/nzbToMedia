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
    section: core.configuration.Section,
    dir_name: str,
    input_name: str = '',
    status: int = 0,
    failed: bool = False,
    client_agent: str = 'manual',
    download_id: str = '',
    input_category: str = '',
    failure_link: str = '',
) -> ProcessResult:

    cfg = dict(core.CFG[section][input_category])

    host = cfg['host']
    port = cfg['port']
    apikey = cfg['apikey']
    wait_for = int(cfg['wait_for'])
    ssl = int(cfg.get('ssl', 0))
    delete_failed = int(cfg['delete_failed'])
    web_root = cfg.get('web_root', '')
    remote_path = int(cfg.get('remote_path', 0))
    scheme = 'https' if ssl else 'http'
    status = int(status)
    if status > 0 and core.NOEXTRACTFAILED:
        extract = 0
    else:
        extract = int(cfg.get('extract', 0))

    route = f'{web_root}/api/v1' if section == 'Lidarr' else f'{web_root}/api'
    url = core.utils.common.create_url(scheme, host, port, route)
    if not server_responding(url):
        logger.error('Server did not respond. Exiting', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - {section} did not respond.'
        )

    if not os.path.isdir(dir_name) and os.path.isfile(dir_name):  # If the input directory is a file, assume single file download and split dir/name.
        dir_name = os.path.split(os.path.normpath(dir_name))[0]

    specific_path = os.path.join(dir_name, str(input_name))
    clean_name = os.path.splitext(specific_path)
    if clean_name[1] == '.nzb':
        specific_path = clean_name[0]
    if os.path.isdir(specific_path):
        dir_name = specific_path

    process_all_exceptions(input_name, dir_name)
    input_name, dir_name = convert_to_ascii(input_name, dir_name)

    if not list_media_files(dir_name, media=False, audio=True, meta=False, archives=False) and list_media_files(dir_name, media=False, audio=False, meta=False, archives=True) and extract:
        logger.debug('Checking for archives to extract in directory: {0}'.format(dir_name))
        core.extract_files(dir_name)
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

        res = force_process(params, url, apikey, input_name, dir_name, section, wait_for)
        if res.status_code in [0, 1]:
            return res

        params = {
            'apikey': apikey,
            'cmd': 'forceProcess',
            'dir': os.path.split(remote_dir(dir_name))[0] if remote_path else os.path.split(dir_name)[0],
        }

        res = force_process(params, url, apikey, input_name, dir_name, section, wait_for)
        if res.status_code in [0, 1]:
            return res

        # The status hasn't changed. uTorrent can resume seeding now.
        logger.warning('The music album does not appear to have changed status after {0} minutes. Please check your Logs'.format(wait_for), section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - No change in wanted status'
        )

    elif status == 0 and section == 'Lidarr':
        route = f'{web_root}/api/v1/command'
        url = core.utils.common.create_url(scheme, host, port, route)
        headers = {'X-Api-Key': apikey}
        if remote_path:
            logger.debug('remote_path: {0}'.format(remote_dir(dir_name)), section)
            data = {'name': 'Rename', 'path': remote_dir(dir_name)}
        else:
            logger.debug('path: {0}'.format(dir_name), section)
            data = {'name': 'Rename', 'path': dir_name}
        data = json.dumps(data)
        try:
            logger.debug('Opening URL: {0} with data: {1}'.format(url, data), section)
            r = requests.post(url, data=data, headers=headers, stream=True, verify=False, timeout=(30, 1800))
        except requests.ConnectionError:
            logger.error('Unable to open URL: {0}'.format(url), section)
            return ProcessResult.failure(
                f'{section}: Failed to post-process - Unable to connect to '
                f'{section}'
            )

        try:
            res = r.json()
            scan_id = int(res['id'])
            logger.debug('Scan started with id: {0}'.format(scan_id), section)
        except Exception as e:
            logger.warning('No scan id was returned due to: {0}'.format(e), section)
            return ProcessResult.failure(
                f'{section}: Failed to post-process - Unable to start scan'
            )

        n = 0
        params = {}
        url = '{0}/{1}'.format(url, scan_id)
        while n < 6:  # set up wait_for minutes to see if command completes..
            time.sleep(10 * wait_for)
            command_status = command_complete(url, params, headers, section)
            if command_status and command_status in ['completed', 'failed']:
                break
            n += 1
        if command_status:
            logger.debug('The Scan command return status: {0}'.format(command_status), section)
        if not os.path.exists(dir_name):
            logger.debug('The directory {0} has been removed. Renaming was successful.'.format(dir_name), section)
            return ProcessResult.success(
                f'{section}: Successfully post-processed {input_name}'
            )
        elif command_status and command_status in ['completed']:
            logger.debug('The Scan command has completed successfully. Renaming was successful.', section)
            return ProcessResult.success(
                f'{section}: Successfully post-processed {input_name}'
            )
        elif command_status and command_status in ['failed']:
            logger.debug('The Scan command has failed. Renaming was not successful.', section)
            # return ProcessResult.failure(
            #     f'{section}: Failed to post-process {input_name}'
            # )
        else:
            logger.debug('The Scan command did not return status completed. Passing back to {0} to attempt complete download handling.'.format(section), section)
            return ProcessResult(
                message=f'{section}: Passing back to {section} to attempt '
                        f'Complete Download Handling',
                status_code=status,
            )

    else:
        if section == 'Lidarr':
            logger.postprocess('FAILED: The download failed. Sending failed download to {0} for CDH processing'.format(section), section)
            # Return as failed to flag this in the downloader.
            return ProcessResult.failure(
                f'{section}: Download Failed. Sending back to {section}'
            )
        else:
            logger.warning('FAILED DOWNLOAD DETECTED', section)
            if delete_failed and os.path.isdir(dir_name) and not os.path.dirname(dir_name) == dir_name:
                logger.postprocess('Deleting failed files and folder {0}'.format(dir_name), section)
                remove_dir(dir_name)
            # Return as failed to flag this in the downloader.
            return ProcessResult.failure(
                f'{section}: Failed to post-process. {section} does not '
                f'support failed downloads'
            )


def get_status(url, apikey, dir_name):
    logger.debug('Attempting to get current status for release:{0}'.format(os.path.basename(dir_name)))

    params = {
        'apikey': apikey,
        'cmd': 'getHistory',
    }

    logger.debug('Opening URL: {0} with PARAMS: {1}'.format(url, params))

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


def force_process(params, url, apikey, input_name, dir_name, section, wait_for):
    release_status = get_status(url, apikey, dir_name)
    if not release_status:
        logger.error('Could not find a status for {0}, is it in the wanted list ?'.format(input_name), section)

    logger.debug('Opening URL: {0} with PARAMS: {1}'.format(url, params), section)

    try:
        r = requests.get(url, params=params, verify=False, timeout=(30, 300))
    except requests.ConnectionError:
        logger.error('Unable to open URL {0}'.format(url), section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Unable to connect to '
            f'{section}'
        )

    logger.debug('Result: {0}'.format(r.text), section)

    if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        logger.error('Server returned status {0}'.format(r.status_code), section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Server returned status {r.status_code}'
        )
    elif r.text == 'OK':
        logger.postprocess('SUCCESS: Post-Processing started for {0} in folder {1} ...'.format(input_name, dir_name), section)
    else:
        logger.error('FAILED: Post-Processing has NOT started for {0} in folder {1}. exiting!'.format(input_name, dir_name), section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Returned log from {section} '
            f'was not as expected.'
        )

    # we will now wait for this album to be processed before returning to TorrentToMedia and unpausing.
    timeout = time.time() + 60 * wait_for
    while time.time() < timeout:
        current_status = get_status(url, apikey, dir_name)
        if current_status is not None and current_status != release_status:  # Something has changed. CPS must have processed this movie.
            logger.postprocess('SUCCESS: This release is now marked as status [{0}]'.format(current_status), section)
            return ProcessResult.success(
                f'{section}: Successfully post-processed {input_name}'
            )
        if not os.path.isdir(dir_name):
            logger.postprocess('SUCCESS: The input directory {0} has been removed Processing must have finished.'.format(dir_name), section)
            return ProcessResult.success(
                f'{section}: Successfully post-processed {input_name}'
            )
        time.sleep(10 * wait_for)
    # The status hasn't changed.
    return ProcessResult(
        message='no change',
        status_code=2,
    )
