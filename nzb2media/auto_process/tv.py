from __future__ import annotations

import copy
import errno
import json
import os
import time

import requests
from oauthlib.oauth2 import LegacyApplicationClient
from requests_oauthlib import OAuth2Session

import nzb2media
from nzb2media import logger
from nzb2media import transcoder
from nzb2media.auto_process.common import ProcessResult
from nzb2media.auto_process.common import command_complete
from nzb2media.auto_process.common import completed_download_handling
from nzb2media.managers.sickbeard import InitSickBeard
from nzb2media.plugins.subtitles import import_subs
from nzb2media.plugins.subtitles import rename_subs
from nzb2media.scene_exceptions import process_all_exceptions
from nzb2media.utils.common import flatten
from nzb2media.utils.encoding import convert_to_ascii
from nzb2media.utils.files import list_media_files
from nzb2media.utils.network import server_responding
from nzb2media.utils.nzb import report_nzb
from nzb2media.utils.paths import remote_dir
from nzb2media.utils.paths import remove_dir


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
    username = cfg.get('username', '')
    password = cfg.get('password', '')
    api_version = int(cfg.get('api_version', 2))
    sso_username = cfg.get('sso_username', '')
    sso_password = cfg.get('sso_password', '')

    # Params
    delete_failed = int(cfg.get('delete_failed', 0))
    remote_path = int(cfg.get('remote_path', 0))
    wait_for = int(cfg.get('wait_for', 2))

    # Misc
    if status > 0 and nzb2media.NOEXTRACTFAILED:
        extract = 0
    else:
        extract = int(cfg.get('extract', 0))
    chmod_directory = int(str(cfg.get('chmodDirectory', '0')), 8)
    import_mode = cfg.get('importMode', 'Move')
    nzb_extraction_by = cfg.get('nzbExtractionBy', 'Downloader')
    process_method = cfg.get('process_method')
    force = int(cfg.get('force', 0))
    delete_on = int(cfg.get('delete_on', 0))
    ignore_subs = int(cfg.get('ignore_subs', 0))

    # Begin processing

    # Refactor into an OO structure.
    # For now let's do botch the OO and the serialized code, until everything has been migrated.
    init_sickbeard = InitSickBeard(cfg, section, input_category)

    url = nzb2media.utils.common.create_url(scheme, host, port, web_root)
    if server_responding(url):
        # auto-detect correct fork
        # During reactor we also return fork, fork_params. But these are also stored in the object.
        # Should be changed after refactor.
        fork, fork_params = init_sickbeard.auto_fork()
    elif not username and not apikey and not sso_username:
        logger.info(
            'No SickBeard / SiCKRAGE username or Sonarr apikey entered. Performing transcoder functions only',
        )
        fork, fork_params = 'None', {}
    else:
        logger.error('Server did not respond. Exiting', section)
        return ProcessResult.failure(
            f'{section}: Failed to post-process - {section} did not respond.',
        )

    if (
        client_agent == nzb2media.TORRENT_CLIENT_AGENT
        and nzb2media.USE_LINK == 'move-sym'
    ):
        process_method = 'symlink'
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

    # Attempt to create the directory if it doesn't exist and ignore any
    # error stating that it already exists. This fixes a bug where SickRage
    # won't process the directory because it doesn't exist.
    if dir_name:
        try:
            os.makedirs(dir_name)  # Attempt to create the directory
        except OSError as e:
            # Re-raise the error if it wasn't about the directory not existing
            if e.errno != errno.EEXIST:
                raise

    if 'process_method' not in fork_params or (
        client_agent in ['nzbget', 'sabnzbd']
        and nzb_extraction_by != 'Destination'
    ):
        if input_name:
            process_all_exceptions(input_name, dir_name)
            input_name, dir_name = convert_to_ascii(input_name, dir_name)

        # Now check if tv files exist in destination.
        if not list_media_files(
            dir_name, media=True, audio=False, meta=False, archives=False,
        ):
            if (
                list_media_files(
                    dir_name,
                    media=False,
                    audio=False,
                    meta=False,
                    archives=True,
                )
                and extract
            ):
                logger.debug(
                    f'Checking for archives to extract in directory: {dir_name}',
                )
                nzb2media.extract_files(dir_name)
                input_name, dir_name = convert_to_ascii(input_name, dir_name)

        if list_media_files(
            dir_name, media=True, audio=False, meta=False, archives=False,
        ):  # Check that a video exists. if not, assume failed.
            flatten(dir_name)

    # Check video files for corruption
    good_files = 0
    valid_files = 0
    num_files = 0
    for video in list_media_files(
        dir_name, media=True, audio=False, meta=False, archives=False,
    ):
        num_files += 1
        if transcoder.is_video_good(video, status):
            good_files += 1
            if not nzb2media.REQUIRE_LAN or transcoder.is_video_good(
                video, status, require_lan=nzb2media.REQUIRE_LAN,
            ):
                valid_files += 1
                import_subs(video)
                rename_subs(dir_name)
    if num_files > 0:
        if valid_files == num_files and not status == 0:
            logger.info('Found Valid Videos. Setting status Success')
            status = 0
        if valid_files < num_files and status == 0:
            logger.info('Found corrupt videos. Setting status Failed')
            status = 1
            if (
                'NZBOP_VERSION' in os.environ
                and os.environ['NZBOP_VERSION'][0:5] >= '14.0'
            ):
                print('[NZB] MARK=BAD')
            if good_files == num_files:
                logger.debug(
                    f'Video marked as failed due to missing required language: {nzb2media.REQUIRE_LAN}',
                    section,
                )
            else:
                logger.debug(
                    'Video marked as failed due to missing playable audio or video',
                    section,
                )
            if (
                good_files < num_files and failure_link
            ):  # only report corrupt files
                failure_link += '&corrupt=true'
    elif client_agent == 'manual':
        logger.warning(
            f'No media files found in directory {dir_name} to manually process.',
            section,
        )
        # Success (as far as this script is concerned)
        return ProcessResult.success()
    elif nzb_extraction_by == 'Destination':
        logger.info(
            'Check for media files ignored because nzbExtractionBy is set to Destination.',
        )
        if status == 0:
            logger.info('Setting Status Success.')
        else:
            logger.info(
                'Downloader reported an error during download or verification. Processing this as a failed download.',
            )
            status = 1
    else:
        logger.warning(
            f'No media files found in directory {dir_name}. Processing this as a failed download',
            section,
        )
        status = 1
        if (
            'NZBOP_VERSION' in os.environ
            and os.environ['NZBOP_VERSION'][0:5] >= '14.0'
        ):
            print('[NZB] MARK=BAD')

    if (
        status == 0 and nzb2media.TRANSCODE == 1
    ):  # only transcode successful downloads
        result, new_dir_name = transcoder.transcode_directory(dir_name)
        if result == 0:
            logger.debug(
                f'SUCCESS: Transcoding succeeded for files in {dir_name}',
                section,
            )
            dir_name = new_dir_name

            logger.debug(
                f'Config setting \'chmodDirectory\' currently set to {oct(chmod_directory)}',
                section,
            )
            if chmod_directory:
                logger.info(
                    f'Attempting to set the octal permission of \'{oct(chmod_directory)}\' on directory \'{dir_name}\'',
                    section,
                )
                nzb2media.rchmod(dir_name, chmod_directory)
        else:
            logger.error(
                f'FAILED: Transcoding failed for files in {dir_name}', section,
            )
            return ProcessResult.failure(
                f'{section}: Failed to post-process - Transcoding failed',
            )

    # Part of the refactor
    if init_sickbeard.fork_obj:
        init_sickbeard.fork_obj.initialize(
            dir_name, input_name, status, client_agent='manual',
        )

    # configure SB params to pass
    # We don't want to remove params, for the Forks that have been refactored.
    # As we don't want to duplicate this part of the code.
    if not init_sickbeard.fork_obj:
        fork_params['quiet'] = 1
        fork_params['proc_type'] = 'manual'
        if input_name is not None:
            fork_params['nzbName'] = input_name

        for param in copy.copy(fork_params):
            if param == 'failed':
                if status > 1:
                    status = 1
                fork_params[param] = status
                if 'proc_type' in fork_params:
                    del fork_params['proc_type']
                if 'type' in fork_params:
                    del fork_params['type']

            if param == 'return_data':
                fork_params[param] = 0
                if 'quiet' in fork_params:
                    del fork_params['quiet']

            if param == 'type':
                if (
                    'type' in fork_params
                ):  # only set if we haven't already deleted for 'failed' above.
                    fork_params[param] = 'manual'
                if 'proc_type' in fork_params:
                    del fork_params['proc_type']

            if param in [
                'dir_name',
                'dir',
                'proc_dir',
                'process_directory',
                'path',
            ]:
                fork_params[param] = dir_name
                if remote_path:
                    fork_params[param] = remote_dir(dir_name)

            if param == 'process_method':
                if process_method:
                    fork_params[param] = process_method
                else:
                    del fork_params[param]

            if param in ['force', 'force_replace']:
                if force:
                    fork_params[param] = force
                else:
                    del fork_params[param]

            if param in ['delete_on', 'delete']:
                if delete_on:
                    fork_params[param] = delete_on
                else:
                    del fork_params[param]

            if param == 'ignore_subs':
                if ignore_subs:
                    fork_params[param] = ignore_subs
                else:
                    del fork_params[param]

            if param == 'force_next':
                fork_params[param] = 1

        # delete any unused params so we don't pass them to SB by mistake
        [fork_params.pop(k) for k, v in list(fork_params.items()) if v is None]

    if status == 0:
        if section == 'NzbDrone' and not apikey:
            logger.info('No Sonarr apikey entered. Processing completed.')
            return ProcessResult.success(
                f'{section}: Successfully post-processed {input_name}',
            )
        logger.postprocess(
            'SUCCESS: The download succeeded, sending a post-process request',
            section,
        )
    else:
        nzb2media.FAILED = True
        if failure_link:
            report_nzb(failure_link, client_agent)
        if 'failed' in fork_params:
            logger.postprocess(
                f'FAILED: The download failed. Sending \'failed\' process request to {fork} branch',
                section,
            )
        elif section == 'NzbDrone':
            logger.postprocess(
                f'FAILED: The download failed. Sending failed download to {fork} for CDH processing',
                section,
            )
            # Return as failed to flag this in the downloader.
            return ProcessResult.failure(
                f'{section}: Download Failed. Sending back to {section}',
            )
        else:
            logger.postprocess(
                f'FAILED: The download failed. {fork} branch does not handle failed downloads. Nothing to process',
                section,
            )
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
                f'{section}: Failed to post-process. {section} does not support failed downloads',
            )

    route = ''
    if section == 'SickBeard':
        if apikey:
            route = f'{web_root}/api/{apikey}/'
            if 'cmd' not in fork_params:
                prefix = '' if 'SickGear' not in fork else 'sg.'
                fork_params['cmd'] = f'{prefix}postprocess'
        elif fork == 'Stheno':
            route = f'{web_root}/home/postprocess/process_episode'
        else:
            route = f'{web_root}/home/postprocess/processEpisode'
    elif section == 'SiCKRAGE':
        if api_version >= 2:
            route = f'{web_root}/api/v{api_version}/postprocess'
        else:
            route = f'{web_root}/api/v{api_version}/{apikey}/'
    elif section == 'NzbDrone':
        route = f'{web_root}/api/command'
        route2 = f'{web_root}/api/config/downloadClient'
        headers = {'X-Api-Key': apikey}
        # params = {'sortKey': 'series.title', 'page': 1, 'pageSize': 1, 'sortDir': 'asc'}
        if remote_path:
            logger.debug(f'remote_path: {remote_dir(dir_name)}', section)
            data = {
                'name': 'DownloadedEpisodesScan',
                'path': remote_dir(dir_name),
                'downloadClientId': download_id,
                'importMode': import_mode,
            }
        else:
            logger.debug(f'path: {dir_name}', section)
            data = {
                'name': 'DownloadedEpisodesScan',
                'path': dir_name,
                'downloadClientId': download_id,
                'importMode': import_mode,
            }
        if not download_id:
            data.pop('downloadClientId')
    url = nzb2media.utils.common.create_url(scheme, host, port, route)
    try:
        if section == 'SickBeard':
            if init_sickbeard.fork_obj:
                return init_sickbeard.fork_obj.api_call()
            else:
                s = requests.Session()

                logger.debug(
                    f'Opening URL: {url} with params: {fork_params}', section,
                )
                if not apikey and username and password:
                    login = f'{web_root}/login'
                    login_params = {'username': username, 'password': password}
                    r = s.get(login, verify=False, timeout=(30, 60))
                    if r.status_code in [401, 403] and r.cookies.get('_xsrf'):
                        login_params['_xsrf'] = r.cookies.get('_xsrf')
                    s.post(
                        login,
                        data=login_params,
                        stream=True,
                        verify=False,
                        timeout=(30, 60),
                    )
                r = s.get(
                    url,
                    auth=(username, password),
                    params=fork_params,
                    stream=True,
                    verify=False,
                    timeout=(30, 1800),
                )
        elif section == 'SiCKRAGE':
            s = requests.Session()

            if api_version >= 2 and sso_username and sso_password:
                oauth = OAuth2Session(
                    client=LegacyApplicationClient(
                        client_id=nzb2media.SICKRAGE_OAUTH_CLIENT_ID,
                    ),
                )
                oauth_token = oauth.fetch_token(
                    client_id=nzb2media.SICKRAGE_OAUTH_CLIENT_ID,
                    token_url=nzb2media.SICKRAGE_OAUTH_TOKEN_URL,
                    username=sso_username,
                    password=sso_password,
                )
                s.headers.update(
                    {'Authorization': 'Bearer ' + oauth_token['access_token']},
                )

                params = {
                    'path': fork_params['path'],
                    'failed': str(bool(fork_params['failed'])).lower(),
                    'processMethod': 'move',
                    'forceReplace': str(
                        bool(fork_params['force_replace']),
                    ).lower(),
                    'returnData': str(
                        bool(fork_params['return_data']),
                    ).lower(),
                    'delete': str(bool(fork_params['delete'])).lower(),
                    'forceNext': str(bool(fork_params['force_next'])).lower(),
                    'nzbName': fork_params['nzbName'],
                }
            else:
                params = fork_params

            r = s.get(
                url,
                params=params,
                stream=True,
                verify=False,
                timeout=(30, 1800),
            )
        elif section == 'NzbDrone':
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

    success = False
    queued = False
    started = False
    if section == 'SickBeard':
        if apikey:
            if r.json()['result'] == 'success':
                success = True
        else:
            for line in r.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    logger.postprocess(line, section)
                    if 'Moving file from' in line:
                        input_name = os.path.split(line)[1]
                    if 'added to the queue' in line:
                        queued = True
                    if (
                        'Processing succeeded' in line
                        or 'Successfully processed' in line
                    ):
                        success = True

        if queued:
            time.sleep(60)
    elif section == 'SiCKRAGE':
        if api_version >= 2:
            success = True
        else:
            if r.json()['result'] == 'success':
                success = True
    elif section == 'NzbDrone':
        try:
            res = r.json()
            scan_id = int(res['id'])
            logger.debug(f'Scan started with id: {scan_id}', section)
            started = True
        except Exception as e:
            logger.warning(f'No scan id was returned due to: {e}', section)
            scan_id = None
            started = False

    if (
        status != 0
        and delete_failed
        and not os.path.dirname(dir_name) == dir_name
    ):
        logger.postprocess(
            f'Deleting failed files and folder {dir_name}', section,
        )
        remove_dir(dir_name)

    if success:
        return ProcessResult.success(
            f'{section}: Successfully post-processed {input_name}',
        )
    elif section == 'NzbDrone' and started:
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

        url2 = nzb2media.utils.common.create_url(scheme, host, port, route)
        if completed_download_handling(url2, headers, section=section):
            logger.debug(
                f'The Scan command did not return status completed, but complete Download Handling is enabled. Passing back to {section}.',
                section,
            )
            return ProcessResult(
                message=f'{section}: Complete DownLoad Handling is enabled. '
                f'Passing back to {section}',
                status_code=status,
            )
        else:
            logger.warning(
                'The Scan command did not return a valid status. Renaming was not successful.',
                section,
            )
            return ProcessResult.failure(
                f'{section}: Failed to post-process {input_name}',
            )
    else:
        # We did not receive Success confirmation.
        return ProcessResult.failure(
            f'{section}: Failed to post-process - Returned log from {section} '
            f'was not as expected.',
        )
