# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import copy
import errno
import json
import os
import time

import requests

import core
from core import logger, transcoder
from core.auto_process.common import (
    ProcessResult,
    command_complete,
    completed_download_handling,
)
from core.forks import auto_fork
from core.plugins.downloaders.nzb.utils import report_nzb
from core.plugins.subtitles import import_subs
from core.scene_exceptions import process_all_exceptions
from core.utils import (
    convert_to_ascii,
    flatten,
    list_media_files,
    remote_dir,
    remove_dir,
    server_responding,
)

requests.packages.urllib3.disable_warnings()


def process(section, dir_name, input_name=None, failed=False, client_agent='manual', download_id=None, input_category=None, failure_link=None):

    cfg = dict(core.CFG[section][input_category])

    host = cfg['host']
    port = cfg['port']
    ssl = int(cfg.get('ssl', 0))
    web_root = cfg.get('web_root', '')
    protocol = 'https://' if ssl else 'http://'
    username = cfg.get('username', '')
    password = cfg.get('password', '')
    apikey = cfg.get('apikey', '')

    if server_responding('{0}{1}:{2}{3}'.format(protocol, host, port, web_root)):
        # auto-detect correct fork
        fork, fork_params = auto_fork(section, input_category)
    elif not username and not apikey:
        logger.info('No SickBeard username or Sonarr apikey entered. Performing transcoder functions only')
        fork, fork_params = 'None', {}
    else:
        logger.error('Server did not respond. Exiting', section)
        return ProcessResult(
            status_code=1,
            message='{0}: Failed to post-process - {0} did not respond.'.format(section),
        )

    delete_failed = int(cfg.get('delete_failed', 0))
    nzb_extraction_by = cfg.get('nzbExtractionBy', 'Downloader')
    process_method = cfg.get('process_method')
    if client_agent == core.TORRENT_CLIENT_AGENT and core.USE_LINK == 'move-sym':
        process_method = 'symlink'
    remote_path = int(cfg.get('remote_path', 0))
    wait_for = int(cfg.get('wait_for', 2))
    force = int(cfg.get('force', 0))
    delete_on = int(cfg.get('delete_on', 0))
    ignore_subs = int(cfg.get('ignore_subs', 0))
    status = int(failed)
    if status > 0 and core.NOEXTRACTFAILED:
        extract = 0
    else:
        extract = int(cfg.get('extract', 0))
    # get importmode, default to 'Move' for consistency with legacy
    import_mode = cfg.get('importMode', 'Move')

    if not os.path.isdir(dir_name) and os.path.isfile(dir_name):  # If the input directory is a file, assume single file download and split dir/name.
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
    try:
        os.makedirs(dir_name)  # Attempt to create the directory
    except OSError as e:
        # Re-raise the error if it wasn't about the directory not existing
        if e.errno != errno.EEXIST:
            raise

    if 'process_method' not in fork_params or (client_agent in ['nzbget', 'sabnzbd'] and nzb_extraction_by != 'Destination'):
        if input_name:
            process_all_exceptions(input_name, dir_name)
            input_name, dir_name = convert_to_ascii(input_name, dir_name)

        # Now check if tv files exist in destination.
        if not list_media_files(dir_name, media=True, audio=False, meta=False, archives=False):
            if list_media_files(dir_name, media=False, audio=False, meta=False, archives=True) and extract:
                logger.debug('Checking for archives to extract in directory: {0}'.format(dir_name))
                core.extract_files(dir_name)
                input_name, dir_name = convert_to_ascii(input_name, dir_name)

        if list_media_files(dir_name, media=True, audio=False, meta=False, archives=False):  # Check that a video exists. if not, assume failed.
            flatten(dir_name)

    # Check video files for corruption
    good_files = 0
    num_files = 0
    for video in list_media_files(dir_name, media=True, audio=False, meta=False, archives=False):
        num_files += 1
        if transcoder.is_video_good(video, status):
            good_files += 1
            import_subs(video)
    if num_files > 0:
        if good_files == num_files and not status == 0:
            logger.info('Found Valid Videos. Setting status Success')
            status = 0
            failed = 0
        if good_files < num_files and status == 0:
            logger.info('Found corrupt videos. Setting status Failed')
            status = 1
            failed = 1
            if 'NZBOP_VERSION' in os.environ and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
                print('[NZB] MARK=BAD')
            if failure_link:
                failure_link += '&corrupt=true'
    elif client_agent == 'manual':
        logger.warning('No media files found in directory {0} to manually process.'.format(dir_name), section)
        return ProcessResult(
            message='',
            status_code=0,  # Success (as far as this script is concerned)
        )
    elif nzb_extraction_by == 'Destination':
        logger.info('Check for media files ignored because nzbExtractionBy is set to Destination.')
        if int(failed) == 0:
            logger.info('Setting Status Success.')
            status = 0
            failed = 0
        else:
            logger.info('Downloader reported an error during download or verification. Processing this as a failed download.')
            status = 1
            failed = 1
    else:
        logger.warning('No media files found in directory {0}. Processing this as a failed download'.format(dir_name), section)
        status = 1
        failed = 1
        if 'NZBOP_VERSION' in os.environ and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
            print('[NZB] MARK=BAD')

    if status == 0 and core.TRANSCODE == 1:  # only transcode successful downloads
        result, new_dir_name = transcoder.transcode_directory(dir_name)
        if result == 0:
            logger.debug('SUCCESS: Transcoding succeeded for files in {0}'.format(dir_name), section)
            dir_name = new_dir_name

            chmod_directory = int(str(cfg.get('chmodDirectory', '0')), 8)
            logger.debug('Config setting \'chmodDirectory\' currently set to {0}'.format(oct(chmod_directory)), section)
            if chmod_directory:
                logger.info('Attempting to set the octal permission of \'{0}\' on directory \'{1}\''.format(oct(chmod_directory), dir_name), section)
                core.rchmod(dir_name, chmod_directory)
        else:
            logger.error('FAILED: Transcoding failed for files in {0}'.format(dir_name), section)
            return ProcessResult(
                message='{0}: Failed to post-process - Transcoding failed'.format(section),
                status_code=1,
            )

    # configure SB params to pass
    fork_params['quiet'] = 1
    fork_params['proc_type'] = 'manual'
    if input_name is not None:
        fork_params['nzbName'] = input_name

    for param in copy.copy(fork_params):
        if param == 'failed':
            fork_params[param] = failed
            if 'proc_type' in fork_params:
                del fork_params['proc_type']
            if 'type' in fork_params:
                del fork_params['type']

        if param == 'return_data':
            fork_params[param] = 0
            if 'quiet' in fork_params:
                del fork_params['quiet']

        if param == 'type':
            fork_params[param] = 'manual'
            if 'proc_type' in fork_params:
                del fork_params['proc_type']

        if param in ['dir_name', 'dir', 'proc_dir', 'process_directory', 'path']:
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
            return ProcessResult(
                message='{0}: Successfully post-processed {1}'.format(section, input_name),
                status_code=0,
            )
        logger.postprocess('SUCCESS: The download succeeded, sending a post-process request', section)
    else:
        core.FAILED = True
        if failure_link:
            report_nzb(failure_link, client_agent)
        if 'failed' in fork_params:
            logger.postprocess('FAILED: The download failed. Sending \'failed\' process request to {0} branch'.format(fork), section)
        elif section == 'NzbDrone':
            logger.postprocess('FAILED: The download failed. Sending failed download to {0} for CDH processing'.format(fork), section)
            return ProcessResult(
                message='{0}: Download Failed. Sending back to {0}'.format(section),
                status_code=1,  # Return as failed to flag this in the downloader.
            )
        else:
            logger.postprocess('FAILED: The download failed. {0} branch does not handle failed downloads. Nothing to process'.format(fork), section)
            if delete_failed and os.path.isdir(dir_name) and not os.path.dirname(dir_name) == dir_name:
                logger.postprocess('Deleting failed files and folder {0}'.format(dir_name), section)
                remove_dir(dir_name)
            return ProcessResult(
                message='{0}: Failed to post-process. {0} does not support failed downloads'.format(section),
                status_code=1,  # Return as failed to flag this in the downloader.
            )

    url = None
    if section == 'SickBeard':
        if apikey:
            url = '{0}{1}:{2}{3}/api/{4}/?cmd=postprocess'.format(protocol, host, port, web_root, apikey)
        elif fork == 'Stheno':
            url = '{0}{1}:{2}{3}/home/postprocess/process_episode'.format(protocol, host, port, web_root)
        else:
            url = '{0}{1}:{2}{3}/home/postprocess/processEpisode'.format(protocol, host, port, web_root)
    elif section == 'NzbDrone':
        url = '{0}{1}:{2}{3}/api/command'.format(protocol, host, port, web_root)
        url2 = '{0}{1}:{2}{3}/api/config/downloadClient'.format(protocol, host, port, web_root)
        headers = {'X-Api-Key': apikey}
        # params = {'sortKey': 'series.title', 'page': 1, 'pageSize': 1, 'sortDir': 'asc'}
        if remote_path:
            logger.debug('remote_path: {0}'.format(remote_dir(dir_name)), section)
            data = {'name': 'DownloadedEpisodesScan', 'path': remote_dir(dir_name), 'downloadClientId': download_id, 'importMode': import_mode}
        else:
            logger.debug('path: {0}'.format(dir_name), section)
            data = {'name': 'DownloadedEpisodesScan', 'path': dir_name, 'downloadClientId': download_id, 'importMode': import_mode}
        if not download_id:
            data.pop('downloadClientId')
        data = json.dumps(data)

    try:
        if section == 'SickBeard':
            logger.debug('Opening URL: {0} with params: {1}'.format(url, fork_params), section)
            s = requests.Session()
            if not apikey and username and password:
                login = '{0}{1}:{2}{3}/login'.format(protocol, host, port, web_root)
                login_params = {'username': username, 'password': password}
                r = s.get(login, verify=False, timeout=(30, 60))
                if r.status_code == 401 and r.cookies.get('_xsrf'):
                    login_params['_xsrf'] = r.cookies.get('_xsrf')
                s.post(login, data=login_params, stream=True, verify=False, timeout=(30, 60))
            r = s.get(url, auth=(username, password), params=fork_params, stream=True, verify=False, timeout=(30, 1800))
        elif section == 'NzbDrone':
            logger.debug('Opening URL: {0} with data: {1}'.format(url, data), section)
            r = requests.post(url, data=data, headers=headers, stream=True, verify=False, timeout=(30, 1800))
    except requests.ConnectionError:
        logger.error('Unable to open URL: {0}'.format(url), section)
        return ProcessResult(
            message='{0}: Failed to post-process - Unable to connect to {0}'.format(section),
            status_code=1,
        )

    if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
        logger.error('Server returned status {0}'.format(r.status_code), section)
        return ProcessResult(
            message='{0}: Failed to post-process - Server returned status {1}'.format(section, r.status_code),
            status_code=1,
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
                    logger.postprocess('{0}'.format(line), section)
                    if 'Moving file from' in line:
                        input_name = os.path.split(line)[1]
                    if 'added to the queue' in line:
                        queued = True
                    if 'Processing succeeded' in line or 'Successfully processed' in line:
                        success = True

        if queued:
            time.sleep(60)
    elif section == 'NzbDrone':
        try:
            res = json.loads(r.content)
            scan_id = int(res['id'])
            logger.debug('Scan started with id: {0}'.format(scan_id), section)
            started = True
        except Exception as e:
            logger.warning('No scan id was returned due to: {0}'.format(e), section)
            scan_id = None
            started = False

    if status != 0 and delete_failed and not os.path.dirname(dir_name) == dir_name:
        logger.postprocess('Deleting failed files and folder {0}'.format(dir_name), section)
        remove_dir(dir_name)

    if success:
        return ProcessResult(
            message='{0}: Successfully post-processed {1}'.format(section, input_name),
            status_code=0,
        )
    elif section == 'NzbDrone' and started:
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
            return ProcessResult(
                message='{0}: Successfully post-processed {1}'.format(section, input_name),
                status_code=0,
            )
        elif command_status and command_status in ['completed']:
            logger.debug('The Scan command has completed successfully. Renaming was successful.', section)
            return ProcessResult(
                message='{0}: Successfully post-processed {1}'.format(section, input_name),
                status_code=0,
            )
        elif command_status and command_status in ['failed']:
            logger.debug('The Scan command has failed. Renaming was not successful.', section)
            # return ProcessResult(
            #     message='{0}: Failed to post-process {1}'.format(section, input_name),
            #     status_code=1,
            # )
        if completed_download_handling(url2, headers, section=section):
            logger.debug('The Scan command did not return status completed, but complete Download Handling is enabled. Passing back to {0}.'.format(section), section)
            return ProcessResult(
                message='{0}: Complete DownLoad Handling is enabled. Passing back to {0}'.format(section),
                status_code=status,
            )
        else:
            logger.warning('The Scan command did not return a valid status. Renaming was not successful.', section)
            return ProcessResult(
                message='{0}: Failed to post-process {1}'.format(section, input_name),
                status_code=1,
            )
    else:
        return ProcessResult(
            message='{0}: Failed to post-process - Returned log from {0} was not as expected.'.format(section),
            status_code=1,  # We did not receive Success confirmation.
        )
