from __future__ import annotations

import json
import logging
import os
import time

import requests

import nzb2media
import nzb2media.utils.common
from nzb2media import transcoder
from nzb2media.auto_process.common import ProcessResult
from nzb2media.auto_process.common import command_complete
from nzb2media.auto_process.common import completed_download_handling
from nzb2media.plugins.subtitles import import_subs
from nzb2media.plugins.subtitles import rename_subs
from nzb2media.scene_exceptions import process_all_exceptions
from nzb2media.utils.encoding import convert_to_ascii
from nzb2media.utils.files import extract_files
from nzb2media.utils.files import list_media_files
from nzb2media.utils.identification import find_imdbid
from nzb2media.utils.network import find_download
from nzb2media.utils.network import server_responding
from nzb2media.utils.nzb import report_nzb
from nzb2media.utils.paths import rchmod
from nzb2media.utils.paths import remote_dir
from nzb2media.utils.paths import remove_dir

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def process(*, section: str, dir_name: str, input_name: str = '', status: int = 0, client_agent: str = 'manual', download_id: str = '', input_category: str = '', failure_link: str = '') -> ProcessResult:
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
    omdbapikey = cfg.get('omdbapikey', '')
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
    if section != 'Radarr':
        import_mode = None
    no_status_check = int(cfg.get('no_status_check', 0))
    method = cfg.get('method', None)
    if section != 'CouchPotato':
        method = None
    # Begin processing
    imdbid = find_imdbid(dir_name, input_name, omdbapikey)
    if section == 'CouchPotato':
        route = f'{web_root}/api/{apikey}/'
    elif section == 'Radarr':
        route = f'{web_root}/api/v3/command'
        route2 = f'{web_root}/api/v3/config/downloadClient'
        url2 = nzb2media.utils.common.create_url(scheme, host, port, route2)
        headers = {'X-Api-Key': apikey, 'Content-Type': 'application/json'}
    elif section == 'Watcher3':
        route = f'{web_root}/postprocessing'
    else:
        route = web_root
    base_url = nzb2media.utils.common.create_url(scheme, host, port, route)
    if not apikey:
        log.info('No CouchPotato or Radarr apikey entered. Performing transcoder functions only')
        release = None
    elif server_responding(base_url):
        if section == 'CouchPotato':
            release = get_release(base_url, imdbid, download_id)
        else:
            release = None
    else:
        log.error('Server did not respond. Exiting')
        return ProcessResult.failure(f'{section}: Failed to post-process - {section} did not respond.')
    # pull info from release found if available
    release_id = None
    media_id = None
    downloader = None
    release_status_old = None
    if release:
        try:
            release_id = list(release.keys())[0]
            media_id = release[release_id]['media_id']
            download_id = release[release_id]['download_info']['id']
            downloader = release[release_id]['download_info']['downloader']
            release_status_old = release[release_id]['status']
        except Exception:
            pass
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
    if not list_media_files(dir_name, media=True, audio=False, meta=False, archives=False) and list_media_files(dir_name, media=False, audio=False, meta=False, archives=True) and extract:
        log.debug(f'Checking for archives to extract in directory: {dir_name}')
        extract_files(dir_name)
        input_name, dir_name = convert_to_ascii(input_name, dir_name)
    good_files = 0
    valid_files = 0
    num_files = 0
    # Check video files for corruption
    for video in list_media_files(dir_name, media=True, audio=False, meta=False, archives=False):
        num_files += 1
        if transcoder.is_video_good(video, status):
            good_files += 1
            if not nzb2media.REQUIRE_LAN or transcoder.is_video_good(video, status, require_lan=nzb2media.REQUIRE_LAN):
                valid_files += 1
                import_subs(video)
                rename_subs(dir_name)
    if num_files and valid_files == num_files:
        if status:
            log.info(f'Status shown as failed from Downloader, but {good_files} valid video files found. Setting as success.')
            status = 0
    elif num_files and valid_files < num_files:
        log.info('Status shown as success from Downloader, but corrupt video files found. Setting as failed.')
        status = 1
        if 'NZBOP_VERSION' in os.environ and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
            print('[NZB] MARK=BAD')
        if good_files == num_files:
            log.debug(f'Video marked as failed due to missing required language: {nzb2media.REQUIRE_LAN}')
        else:
            log.debug('Video marked as failed due to missing playable audio or video')
        if good_files < num_files and failure_link:  # only report corrupt files
            failure_link += '&corrupt=true'
    elif client_agent == 'manual':
        log.warning(f'No media files found in directory {dir_name} to manually process.')
        return ProcessResult(
            message='',
            status_code=0,  # Success (as far as this script is concerned)
        )
    else:
        log.warning(f'No media files found in directory {dir_name}. Processing this as a failed download')
        status = 1
        if 'NZBOP_VERSION' in os.environ and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
            print('[NZB] MARK=BAD')
    if status == 0:
        if nzb2media.TRANSCODE == 1:
            result, new_dir_name = transcoder.transcode_directory(dir_name)
            if result == 0:
                log.debug(f'Transcoding succeeded for files in {dir_name}')
                dir_name = new_dir_name
                log.debug(f'Config setting \'chmodDirectory\' currently set to {oct(chmod_directory)}')
                if chmod_directory:
                    log.info(f'Attempting to set the octal permission of \'{oct(chmod_directory)}\' on directory \'{dir_name}\'')
                    rchmod(dir_name, chmod_directory)
            else:
                log.error(f'Transcoding failed for files in {dir_name}')
                return ProcessResult(message=f'{section}: Failed to post-process - Transcoding failed', status_code=1)
        for video in list_media_files(dir_name, media=True, audio=False, meta=False, archives=False):
            if not release and '.cp(tt' not in video and imdbid:
                video_name, video_ext = os.path.splitext(video)
                video2 = f'{video_name}.cp({imdbid}){video_ext}'
                if not (client_agent in [nzb2media.TORRENT_CLIENT_AGENT, 'manual'] and nzb2media.USE_LINK == 'move-sym'):
                    log.debug(f'Renaming: {video} to: {video2}')
                    os.rename(video, video2)
        if not apikey:  # If only using Transcoder functions, exit here.
            log.info('No CouchPotato or Radarr or Watcher3 apikey entered. Processing completed.')
            return ProcessResult(message=f'{section}: Successfully post-processed {input_name}', status_code=0)
        params = {'media_folder': remote_dir(dir_name) if remote_path else dir_name}
        if download_id and release_id:
            params['downloader'] = downloader or client_agent
            params['download_id'] = download_id
        if section == 'CouchPotato':
            if method == 'manage':
                command = 'manage.update'
                params.clear()
            else:
                command = 'renamer.scan'
            url = f'{base_url}{command}'
            log.debug(f'Opening URL: {url} with PARAMS: {params}')
            log.debug(f'Starting {method} scan for {input_name}')
        if section == 'Radarr':
            payload = {'name': 'DownloadedMoviesScan', 'path': params['media_folder'], 'downloadClientId': download_id, 'importMode': import_mode}
            if not download_id:
                payload.pop('downloadClientId')
            log.debug(f'Opening URL: {base_url} with PARAMS: {payload}')
            log.debug(f'Starting DownloadedMoviesScan scan for {input_name}')
        if section == 'Watcher3':
            if input_name and os.path.isfile(os.path.join(dir_name, input_name)):
                params['media_folder'] = os.path.join(params['media_folder'], input_name)
            payload = {'apikey': apikey, 'path': params['media_folder'], 'guid': download_id, 'mode': 'complete'}
            if not download_id:
                payload.pop('guid')
            log.debug(f'Opening URL: {base_url} with PARAMS: {payload}')
            log.debug(f'Starting postprocessing scan for {input_name}')
        try:
            if section == 'CouchPotato':
                response = requests.get(url, params=params, verify=False, timeout=(30, 1800))
            elif section == 'Watcher3':
                response = requests.post(base_url, data=payload, verify=False, timeout=(30, 1800))
            else:
                response = requests.post(base_url, data=json.dumps(payload), headers=headers, stream=True, verify=False, timeout=(30, 1800))
        except requests.ConnectionError:
            log.error('Unable to open URL')
            return ProcessResult(message=f'{section}: Failed to post-process - Unable to connect to {section}', status_code=1)
        result = response.json()
        if response.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            log.error(f'Server returned status {response.status_code}')
            return ProcessResult(message=f'{section}: Failed to post-process - Server returned status {response.status_code}', status_code=1)
        if section == 'CouchPotato' and result['success']:
            log.debug(f'SUCCESS: Finished {method} scan for folder {dir_name}')
            if method == 'manage':
                return ProcessResult(message=f'{section}: Successfully post-processed {input_name}', status_code=0)
        elif section == 'Radarr':
            try:
                scan_id = int(result['id'])
                log.debug(f'Scan started with id: {scan_id}')
            except Exception as error:
                log.warning(f'No scan id was returned due to: {error}')
                scan_id = None
        elif section == 'Watcher3' and result['status'] == 'finished':
            update_movie_status = result['tasks']['update_movie_status']
            log.debug(f'Watcher3 updated status to {section}')
            if update_movie_status == 'Finished':
                return ProcessResult(message=f'{section}: Successfully post-processed {input_name}', status_code=status)
            return ProcessResult(message=f'{section}: Failed to post-process - changed status to {update_movie_status}', status_code=1)
        else:
            log.error(f'FAILED: {method} scan was unable to finish for folder {dir_name}. exiting!')
            return ProcessResult(message=f'{section}: Failed to post-process - Server did not return success', status_code=1)
    else:
        nzb2media.FAILED = True
        log.debug(f'FAILED DOWNLOAD DETECTED FOR {input_name}')
        if failure_link:
            report_nzb(failure_link, client_agent)
        if section == 'Radarr':
            log.debug(f'SUCCESS: Sending failed download to {section} for CDH processing')
            return ProcessResult(
                message=f'{section}: Sending failed download back to {section}',
                status_code=1,  # Return as failed to flag this in the downloader.
            )  # Return failed flag, but log the event as successful.
        if section == 'Watcher3':
            log.debug(f'Sending failed download to {section} for CDH processing')
            path = remote_dir(dir_name) if remote_path else dir_name
            if input_name and os.path.isfile(os.path.join(dir_name, input_name)):
                path = os.path.join(path, input_name)
            payload = {'apikey': apikey, 'path': path, 'guid': download_id, 'mode': 'failed'}
            response = requests.post(base_url, data=payload, verify=False, timeout=(30, 1800))
            result = response.json()
            log.debug(f'Watcher3 response: {result}')
            if result['status'] == 'finished':
                return ProcessResult(
                    message=f'{section}: Sending failed download back to {section}',
                    status_code=1,  # Return as failed to flag this in the downloader.
                )  # Return failed flag, but log the event as successful.
        if delete_failed and os.path.isdir(dir_name) and not os.path.dirname(dir_name) == dir_name:
            log.debug(f'Deleting failed files and folder {dir_name}')
            remove_dir(dir_name)
        if not release_id and not media_id:
            log.error(f'Could not find a downloaded movie in the database matching {input_name}, exiting!')
            return ProcessResult(message='{0}: Failed to post-process - Failed download not found in {0}'.format(section), status_code=1)
        if release_id:
            log.debug(f'Setting failed release {input_name} to ignored ...')
            url = f'{base_url}release.ignore'
            params = {'id': release_id}
            log.debug(f'Opening URL: {url} with PARAMS: {params}')
            try:
                response = requests.get(url, params=params, verify=False, timeout=(30, 120))
            except requests.ConnectionError:
                log.error(f'Unable to open URL {url}')
                return ProcessResult(message='{0}: Failed to post-process - Unable to connect to {0}'.format(section), status_code=1)
            result = response.json()
            if response.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                log.error(f'Server returned status {response.status_code}')
                return ProcessResult(status_code=1, message=f'{section}: Failed to post-process - Server returned status {response.status_code}')
            if result['success']:
                log.debug(f'SUCCESS: {input_name} has been set to ignored ...')
            else:
                log.warning(f'FAILED: Unable to set {input_name} to ignored!')
                return ProcessResult(message=f'{section}: Failed to post-process - Unable to set {input_name} to ignored', status_code=1)
        log.debug('Trying to snatch the next highest ranked release.')
        url = f'{base_url}movie.searcher.try_next'
        log.debug(f'Opening URL: {url}')
        try:
            response = requests.get(url, params={'media_id': media_id}, verify=False, timeout=(30, 600))
        except requests.ConnectionError:
            log.error(f'Unable to open URL {url}')
            return ProcessResult.failure(f'{section}: Failed to post-process - Unable to connect to {section}')
        result = response.json()
        if response.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            log.error(f'Server returned status {response.status_code}')
            return ProcessResult.failure(f'{section}: Failed to post-process - Server returned status {response.status_code}')
        if result['success']:
            log.debug('SUCCESS: Snatched the next highest release ...')
            return ProcessResult.success(f'{section}: Successfully snatched next highest release')
        log.debug('SUCCESS: Unable to find a new release to snatch now. CP will keep searching!')
        return ProcessResult.success(f'{section}: No new release found now. {section} will keep searching')
    # Added a release that was not in the wanted list so confirm rename
    # successful by finding this movie media.list.
    if not release:
        # we don't want to filter new releases based on this.
        download_id = ''
    if no_status_check:
        return ProcessResult.success(f'{section}: Successfully processed but no change in status confirmed')
    # we will now check to see if CPS has finished renaming before returning to TorrentToMedia and unpausing.
    timeout = time.time() + 60 * wait_for
    while time.time() < timeout:  # only wait 2 (default) minutes, then return.
        log.debug('Checking for status change, please stand by ...')
        if section == 'CouchPotato':
            release = get_release(base_url, imdbid, download_id, release_id)
            scan_id = None
        else:
            release = None
        if release:
            try:
                release_id = list(release.keys())[0]
                release_status_new = release[release_id]['status']
                if release_status_old is None:  # we didn't have a release before, but now we do.
                    title = release[release_id]['title']
                    log.debug(f'SUCCESS: Movie {title} has now been added to CouchPotato with release status of [{str(release_status_new).upper()}]')
                    return ProcessResult.success(f'{section}: Successfully post-processed {input_name}')
                if release_status_new != release_status_old:
                    log.debug(f'SUCCESS: Release {release_id} has now been marked with a status of [{str(release_status_new).upper()}]')
                    return ProcessResult.success(f'{section}: Successfully post-processed {input_name}')
            except Exception:
                pass
        elif scan_id:
            url = f'{base_url}/{scan_id}'
            command_status = command_complete(url, params, headers, section)
            if command_status:
                log.debug(f'The Scan command return status: {command_status}')
                if command_status in ['completed']:
                    log.debug('The Scan command has completed successfully. Renaming was successful.')
                    return ProcessResult.success(f'{section}: Successfully post-processed {input_name}')
                if command_status in ['failed']:
                    log.debug('The Scan command has failed. Renaming was not successful.')
                    # return ProcessResult(message='{0}: Failed to post-process {1}'.format(section, input_name), status_code=1)
        if not os.path.isdir(dir_name):
            log.debug(f'SUCCESS: Input Directory [{dir_name}] has been processed and removed')
            return ProcessResult.success(f'{section}: Successfully post-processed {input_name}')
        if not list_media_files(dir_name, media=True, audio=False, meta=False, archives=True):
            log.debug(f'SUCCESS: Input Directory [{dir_name}] has no remaining media files. This has been fully processed.')
            return ProcessResult.success(f'{section}: Successfully post-processed {input_name}')
        # pause and let CouchPotatoServer/Radarr catch its breath
        time.sleep(10 * wait_for)
    # The status hasn't changed. we have waited wait_for minutes which is more than enough. uTorrent can resume seeding now.
    if section == 'Radarr' and completed_download_handling(url2, headers, section=section):
        log.debug(f'The Scan command did not return status completed, but complete Download Handling is enabled. Passing back to {section}.')
        return ProcessResult.success(f'{section}: Complete DownLoad Handling is enabled. Passing back to {section}')
    log.warning(f'{input_name} does not appear to have changed status after {wait_for} minutes, Please check your logs.')
    return ProcessResult.failure(f'{section}: Failed to post-process - No change in status')


def get_release(base_url, imdb_id=None, download_id=None, release_id=None):
    results = {}
    params = {}
    # determine cmd and params to send to CouchPotato to get our results
    section = 'movies'
    cmd = 'media.list'
    if release_id or imdb_id:
        section = 'media'
        cmd = 'media.get'
        params['id'] = release_id or imdb_id
    if not (release_id or imdb_id or download_id):
        log.debug('No information available to filter CP results')
        return results
    url = f'{base_url}{cmd}'
    log.debug(f'Opening URL: {url} with PARAMS: {params}')
    try:
        response = requests.get(url, params=params, verify=False, timeout=(30, 60))
    except requests.ConnectionError:
        log.error(f'Unable to open URL {url}')
        return results
    try:
        result = response.json()
    except ValueError:
        # ValueError catches simplejson's JSONDecodeError and json's ValueError
        log.error('CouchPotato returned the following non-json data')
        for line in response.iter_lines():
            log.error(line)
        return results
    if not result['success']:
        if 'error' in result:
            log.error(result['error'])
        else:
            id_param = params['id']
            log.error(f'no media found for id {id_param}')
        return results
    # Gather release info and return it back, no need to narrow results
    if release_id:
        try:
            key = result[section]['_id']
            results[key] = result[section]
            return results
        except Exception:
            pass
    # Gather release info and proceed with trying to narrow results to one release choice
    movies = result[section]
    if not isinstance(movies, list):
        movies = [movies]
    for movie in movies:
        if movie['status'] not in ['active', 'done']:
            continue
        releases = movie['releases']
        if not releases:
            continue
        for release in releases:
            try:
                if release['status'] not in ['snatched', 'downloaded', 'done']:
                    continue
                if download_id:
                    if download_id.lower() != release['download_info']['id'].lower():
                        continue
                key = release['_id']
                results[key] = release
                results[key]['title'] = movie['title']
            except Exception:
                continue
    # Narrow results by removing old releases by comparing their last_edit field
    if len(results) > 1:
        rem_id = set()
        for key, val1 in results.items():
            for val2 in results.values():
                try:
                    if val2['last_edit'] > val1['last_edit']:
                        rem_id.add(key)
                except Exception:
                    continue
        for ea_id in rem_id:
            results.pop(ea_id)
    # Search downloads on clients for a match to try and narrow our results down to 1
    if len(results) > 1:
        rem_id = set()
        for key, val1 in results.items():
            try:
                if not find_download(str(val1['download_info']['downloader']).lower(), val1['download_info']['id']):
                    rem_id.add(key)
            except Exception:
                continue
        for ea_id in rem_id:
            results.pop(ea_id)
    return results
