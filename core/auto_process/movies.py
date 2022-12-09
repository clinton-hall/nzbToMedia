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

import core
from core import logger
from core import transcoder
from core.auto_process.common import command_complete
from core.auto_process.common import completed_download_handling
from core.auto_process.common import ProcessResult
from core.auto_process.managers.sickbeard import InitSickBeard
from core.plugins.downloaders.nzb.utils import report_nzb
from core.plugins.subtitles import import_subs
from core.plugins.subtitles import rename_subs
from core.scene_exceptions import process_all_exceptions
from core.utils import convert_to_ascii
from core.utils import find_download
from core.utils import find_imdbid
from core.utils import flatten
from core.utils import list_media_files
from core.utils import remote_dir
from core.utils import remove_dir
from core.utils import server_responding


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
    omdbapikey = cfg.get('omdbapikey', '')

    # Params
    delete_failed = int(cfg.get('delete_failed', 0))
    remote_path = int(cfg.get('remote_path', 0))
    wait_for = int(cfg.get('wait_for', 2))

    # Misc
    if status > 0 and core.NOEXTRACTFAILED:
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
        url2 = core.utils.common.create_url(scheme, host, port, route2)
        headers = {'X-Api-Key': apikey, 'Content-Type': 'application/json'}
    elif section == 'Watcher3':
        route = f'{web_root}/postprocessing'
    else:
        route = web_root
    base_url = core.utils.common.create_url(scheme, host, port, route)
    if not apikey:
        logger.info('No CouchPotato or Radarr apikey entered. Performing transcoder functions only')
        release = None
    elif server_responding(base_url):
        if section == 'CouchPotato':
            release = get_release(base_url, imdbid, download_id)
        else:
            release = None
    else:
        logger.error('Server did not respond. Exiting', section)
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
        logger.debug(f'Checking for archives to extract in directory: {dir_name}')
        core.extract_files(dir_name)
        input_name, dir_name = convert_to_ascii(input_name, dir_name)

    good_files = 0
    valid_files = 0
    num_files = 0
    # Check video files for corruption
    for video in list_media_files(dir_name, media=True, audio=False, meta=False, archives=False):
        num_files += 1
        if transcoder.is_video_good(video, status):
            good_files += 1
            if not core.REQUIRE_LAN or transcoder.is_video_good(video, status, require_lan=core.REQUIRE_LAN):
                valid_files += 1
                import_subs(video)
                rename_subs(dir_name)
    if num_files and valid_files == num_files:
        if status:
            logger.info(f'Status shown as failed from Downloader, but {good_files} valid video files found. Setting as success.', section)
            status = 0
    elif num_files and valid_files < num_files:
        logger.info('Status shown as success from Downloader, but corrupt video files found. Setting as failed.', section)
        status = 1
        if 'NZBOP_VERSION' in os.environ and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
            print('[NZB] MARK=BAD')
        if good_files == num_files:
            logger.debug(f'Video marked as failed due to missing required language: {core.REQUIRE_LAN}', section)
        else:
            logger.debug('Video marked as failed due to missing playable audio or video', section)
        if good_files < num_files and failure_link:  # only report corrupt files
            failure_link += '&corrupt=true'
    elif client_agent == 'manual':
        logger.warning(f'No media files found in directory {dir_name} to manually process.', section)
        return ProcessResult(
            message='',
            status_code=0,  # Success (as far as this script is concerned)
        )
    else:
        logger.warning(f'No media files found in directory {dir_name}. Processing this as a failed download', section)
        status = 1
        if 'NZBOP_VERSION' in os.environ and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
            print('[NZB] MARK=BAD')

    if status == 0:
        if core.TRANSCODE == 1:
            result, new_dir_name = transcoder.transcode_directory(dir_name)
            if result == 0:
                logger.debug(f'Transcoding succeeded for files in {dir_name}', section)
                dir_name = new_dir_name

                logger.debug(f'Config setting \'chmodDirectory\' currently set to {oct(chmod_directory)}', section)
                if chmod_directory:
                    logger.info(f'Attempting to set the octal permission of \'{oct(chmod_directory)}\' on directory \'{dir_name}\'', section)
                    core.rchmod(dir_name, chmod_directory)
            else:
                logger.error(f'Transcoding failed for files in {dir_name}', section)
                return ProcessResult(
                    message=f'{section}: Failed to post-process - Transcoding failed',
                    status_code=1,
                )
        for video in list_media_files(dir_name, media=True, audio=False, meta=False, archives=False):
            if not release and '.cp(tt' not in video and imdbid:
                video_name, video_ext = os.path.splitext(video)
                video2 = f'{video_name}.cp({imdbid}){video_ext}'
                if not (client_agent in [core.TORRENT_CLIENT_AGENT, 'manual'] and core.USE_LINK == 'move-sym'):
                    logger.debug(f'Renaming: {video} to: {video2}')
                    os.rename(video, video2)

        if not apikey:  # If only using Transcoder functions, exit here.
            logger.info('No CouchPotato or Radarr or Watcher3 apikey entered. Processing completed.')
            return ProcessResult(
                message=f'{section}: Successfully post-processed {input_name}',
                status_code=0,
            )

        params = {
            'media_folder': remote_dir(dir_name) if remote_path else dir_name,
        }

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
            logger.debug(f'Opening URL: {url} with PARAMS: {params}', section)
            logger.postprocess(f'Starting {method} scan for {input_name}', section)

        if section == 'Radarr':
            payload = {'name': 'DownloadedMoviesScan', 'path': params['media_folder'], 'downloadClientId': download_id, 'importMode': import_mode}
            if not download_id:
                payload.pop('downloadClientId')
            logger.debug(f'Opening URL: {base_url} with PARAMS: {payload}', section)
            logger.postprocess(f'Starting DownloadedMoviesScan scan for {input_name}', section)

        if section == 'Watcher3':
            if input_name and os.path.isfile(os.path.join(dir_name, input_name)):
                params['media_folder'] = os.path.join(params['media_folder'], input_name)
            payload = {'apikey': apikey, 'path': params['media_folder'], 'guid': download_id, 'mode': 'complete'}
            if not download_id:
                payload.pop('guid')
            logger.debug(f'Opening URL: {base_url} with PARAMS: {payload}', section)
            logger.postprocess(f'Starting postprocessing scan for {input_name}', section)

        try:
            if section == 'CouchPotato':
                r = requests.get(url, params=params, verify=False, timeout=(30, 1800))
            elif section == 'Watcher3':
                r = requests.post(base_url, data=payload, verify=False, timeout=(30, 1800))
            else:
                r = requests.post(base_url, data=json.dumps(payload), headers=headers, stream=True, verify=False, timeout=(30, 1800))
        except requests.ConnectionError:
            logger.error('Unable to open URL', section)
            return ProcessResult(
                message='{0}: Failed to post-process - Unable to connect to {0}'.format(section),
                status_code=1,
            )

        result = r.json()
        if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error(f'Server returned status {r.status_code}', section)
            return ProcessResult(
                message=f'{section}: Failed to post-process - Server returned status {r.status_code}',
                status_code=1,
            )
        elif section == 'CouchPotato' and result['success']:
            logger.postprocess(f'SUCCESS: Finished {method} scan for folder {dir_name}', section)
            if method == 'manage':
                return ProcessResult(
                    message=f'{section}: Successfully post-processed {input_name}',
                    status_code=0,
                )
        elif section == 'Radarr':
            try:
                scan_id = int(result['id'])
                logger.debug(f'Scan started with id: {scan_id}', section)
            except Exception as e:
                logger.warning(f'No scan id was returned due to: {e}', section)
                scan_id = None
        elif section == 'Watcher3' and result['status'] == 'finished':
            update_movie_status = result['tasks']['update_movie_status']
            logger.postprocess('Watcher3 updated status to {}'.format())
            if update_movie_status == 'Finished':
                return ProcessResult(
                    message=f'{section}: Successfully post-processed {input_name}',
                    status_code=status,
                )
            else:
                return ProcessResult(
                    message=f'{section}: Failed to post-process - changed status to {update_movie_status}',
                    status_code=1,
                )
        else:
            logger.error(
                f'FAILED: {method} scan was unable to finish for folder {dir_name}. exiting!',
                section,
            )
            return ProcessResult(
                message=f'{section}: Failed to post-process - Server did not return success',
                status_code=1,
            )
    else:
        core.FAILED = True
        logger.postprocess(f'FAILED DOWNLOAD DETECTED FOR {input_name}', section)
        if failure_link:
            report_nzb(failure_link, client_agent)

        if section == 'Radarr':
            logger.postprocess(f'SUCCESS: Sending failed download to {section} for CDH processing', section)
            return ProcessResult(
                message='{0}: Sending failed download back to {0}'.format(section),
                status_code=1,  # Return as failed to flag this in the downloader.
            )  # Return failed flag, but log the event as successful.
        elif section == 'Watcher3':
            logger.postprocess(f'Sending failed download to {section} for CDH processing', section)
            path = remote_dir(dir_name) if remote_path else dir_name
            if input_name and os.path.isfile(os.path.join(dir_name, input_name)):
                path = os.path.join(path, input_name)
            payload = {'apikey': apikey, 'path': path, 'guid': download_id, 'mode': 'failed'}
            r = requests.post(base_url, data=payload, verify=False, timeout=(30, 1800))
            result = r.json()
            logger.postprocess(f'Watcher3 response: {result}')
            if result['status'] == 'finished':
                return ProcessResult(
                    message='{0}: Sending failed download back to {0}'.format(section),
                    status_code=1,  # Return as failed to flag this in the downloader.
                )  # Return failed flag, but log the event as successful.

        if delete_failed and os.path.isdir(dir_name) and not os.path.dirname(dir_name) == dir_name:
            logger.postprocess(f'Deleting failed files and folder {dir_name}', section)
            remove_dir(dir_name)

        if not release_id and not media_id:
            logger.error(
                f'Could not find a downloaded movie in the database matching {input_name}, exiting!',
                section,
            )
            return ProcessResult(
                message='{0}: Failed to post-process - Failed download not found in {0}'.format(section),
                status_code=1,
            )

        if release_id:
            logger.postprocess(f'Setting failed release {input_name} to ignored ...', section)

            url = f'{base_url}release.ignore'
            params = {'id': release_id}

            logger.debug(f'Opening URL: {url} with PARAMS: {params}', section)

            try:
                r = requests.get(url, params=params, verify=False, timeout=(30, 120))
            except requests.ConnectionError:
                logger.error(f'Unable to open URL {url}', section)
                return ProcessResult(
                    message='{0}: Failed to post-process - Unable to connect to {0}'.format(section),
                    status_code=1,
                )

            result = r.json()
            if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                logger.error(f'Server returned status {r.status_code}', section)
                return ProcessResult(
                    status_code=1,
                    message=f'{section}: Failed to post-process - Server returned status {r.status_code}',
                )
            elif result['success']:
                logger.postprocess(f'SUCCESS: {input_name} has been set to ignored ...', section)
            else:
                logger.warning(f'FAILED: Unable to set {input_name} to ignored!', section)
                return ProcessResult(
                    message=f'{section}: Failed to post-process - Unable to set {input_name} to ignored',
                    status_code=1,
                )

        logger.postprocess('Trying to snatch the next highest ranked release.', section)

        url = f'{base_url}movie.searcher.try_next'
        logger.debug(f'Opening URL: {url}', section)

        try:
            r = requests.get(url, params={'media_id': media_id}, verify=False, timeout=(30, 600))
        except requests.ConnectionError:
            logger.error(f'Unable to open URL {url}', section)
            return ProcessResult.failure(
                f'{section}: Failed to post-process - Unable to connect to '
                f'{section}',
            )

        result = r.json()
        if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error(f'Server returned status {r.status_code}', section)
            return ProcessResult.failure(
                f'{section}: Failed to post-process - Server returned status '
                f'{r.status_code}',
            )
        elif result['success']:
            logger.postprocess('SUCCESS: Snatched the next highest release ...', section)
            return ProcessResult.success(
                f'{section}: Successfully snatched next highest release',
            )
        else:
            logger.postprocess('SUCCESS: Unable to find a new release to snatch now. CP will keep searching!', section)
            return ProcessResult.success(
                f'{section}: No new release found now. '
                f'{section} will keep searching',
            )

    # Added a release that was not in the wanted list so confirm rename successful by finding this movie media.list.
    if not release:
        download_id = None  # we don't want to filter new releases based on this.

    if no_status_check:
        return ProcessResult.success(
            f'{section}: Successfully processed but no change in status '
            f'confirmed',
        )

    # we will now check to see if CPS has finished renaming before returning to TorrentToMedia and unpausing.
    timeout = time.time() + 60 * wait_for
    while time.time() < timeout:  # only wait 2 (default) minutes, then return.
        logger.postprocess('Checking for status change, please stand by ...', section)
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
                    logger.postprocess(f'SUCCESS: Movie {title} has now been added to CouchPotato with release status of [{str(release_status_new).upper()}]', section)
                    return ProcessResult.success(
                        f'{section}: Successfully post-processed {input_name}',
                    )

                if release_status_new != release_status_old:
                    logger.postprocess(f'SUCCESS: Release {release_id} has now been marked with a status of [{str(release_status_new).upper()}]', section)
                    return ProcessResult.success(
                        f'{section}: Successfully post-processed {input_name}',
                    )
            except Exception:
                pass
        elif scan_id:
            url = f'{base_url}/{scan_id}'
            command_status = command_complete(url, params, headers, section)
            if command_status:
                logger.debug(f'The Scan command return status: {command_status}', section)
                if command_status in ['completed']:
                    logger.debug('The Scan command has completed successfully. Renaming was successful.', section)
                    return ProcessResult.success(
                        f'{section}: Successfully post-processed {input_name}',
                    )
                elif command_status in ['failed']:
                    logger.debug('The Scan command has failed. Renaming was not successful.', section)
                    # return ProcessResult(
                    #     message='{0}: Failed to post-process {1}'.format(section, input_name),
                    #     status_code=1,
                    # )

        if not os.path.isdir(dir_name):
            logger.postprocess(f'SUCCESS: Input Directory [{dir_name}] has been processed and removed', section)
            return ProcessResult.success(
                f'{section}: Successfully post-processed {input_name}',
            )

        elif not list_media_files(dir_name, media=True, audio=False, meta=False, archives=True):
            logger.postprocess(f'SUCCESS: Input Directory [{dir_name}] has no remaining media files. This has been fully processed.', section)
            return ProcessResult.success(
                f'{section}: Successfully post-processed {input_name}',
            )

        # pause and let CouchPotatoServer/Radarr catch its breath
        time.sleep(10 * wait_for)

    # The status hasn't changed. we have waited wait_for minutes which is more than enough. uTorrent can resume seeding now.
    if section == 'Radarr' and completed_download_handling(url2, headers, section=section):
        logger.debug(f'The Scan command did not return status completed, but complete Download Handling is enabled. Passing back to {section}.', section)
        return ProcessResult.success(
            f'{section}: Complete DownLoad Handling is enabled. Passing back '
            f'to {section}',
        )
    logger.warning(
        f'{input_name} does not appear to have changed status after {wait_for} minutes, Please check your logs.',
        section,
    )

    return ProcessResult.failure(
        f'{section}: Failed to post-process - No change in status',
    )


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
        logger.debug('No information available to filter CP results')
        return results

    url = f'{base_url}{cmd}'
    logger.debug(f'Opening URL: {url} with PARAMS: {params}')

    try:
        r = requests.get(url, params=params, verify=False, timeout=(30, 60))
    except requests.ConnectionError:
        logger.error(f'Unable to open URL {url}')
        return results

    try:
        result = r.json()
    except ValueError:
        # ValueError catches simplejson's JSONDecodeError and json's ValueError
        logger.error('CouchPotato returned the following non-json data')
        for line in r.iter_lines():
            logger.error(line)
        return results

    if not result['success']:
        if 'error' in result:
            logger.error(result['error'])
        else:
            id_param = params['id']
            logger.error(f'no media found for id {id_param}')
        return results

    # Gather release info and return it back, no need to narrow results
    if release_id:
        try:
            cur_id = result[section]['_id']
            results[cur_id] = result[section]
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

                cur_id = release['_id']
                results[cur_id] = release
                results[cur_id]['title'] = movie['title']
            except Exception:
                continue

    # Narrow results by removing old releases by comparing their last_edit field
    if len(results) > 1:
        rem_id = set()
        for id1, x1 in results.items():
            for x2 in results.values():
                try:
                    if x2['last_edit'] > x1['last_edit']:
                        rem_id.add(id1)
                except Exception:
                    continue
        for id in rem_id:
            results.pop(id)

    # Search downloads on clients for a match to try and narrow our results down to 1
    if len(results) > 1:
        rem_id = set()
        for cur_id, x in results.items():
            try:
                if not find_download(str(x['download_info']['downloader']).lower(), x['download_info']['id']):
                    rem_id.add(cur_id)
            except Exception:
                continue
        for id in rem_id:
            results.pop(id)

    return results
