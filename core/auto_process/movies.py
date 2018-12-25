# coding=utf-8

import json
import os
import time

import requests

import core
from core import logger, transcoder
from core.scene_exceptions import process_all_exceptions
from core.utils import convert_to_ascii, find_download, find_imdbid, import_subs, list_media_files, remote_dir, remove_dir, report_nzb, server_responding

requests.packages.urllib3.disable_warnings()


class Movie(object):
    def process(self, section, dir_name, input_name=None, status=0, client_agent="manual", download_id="", input_category=None, failure_link=None):

        cfg = dict(core.CFG[section][input_category])

        host = cfg["host"]
        port = cfg["port"]
        apikey = cfg["apikey"]
        if section == "CouchPotato":
            method = cfg["method"]
        else:
            method = None
        # added importMode for Radarr config
        if section == "Radarr":
            import_mode = cfg.get("importMode", "Move")
        else:
            import_mode = None
        delete_failed = int(cfg["delete_failed"])
        wait_for = int(cfg["wait_for"])
        ssl = int(cfg.get("ssl", 0))
        web_root = cfg.get("web_root", "")
        remote_path = int(cfg.get("remote_path", 0))
        protocol = "https://" if ssl else "http://"
        omdbapikey = cfg.get("omdbapikey", "")
        status = int(status)
        if status > 0 and core.NOEXTRACTFAILED:
            extract = 0
        else:
            extract = int(cfg.get("extract", 0))

        imdbid = find_imdbid(dir_name, input_name, omdbapikey)
        if section == "CouchPotato":
            base_url = "{0}{1}:{2}{3}/api/{4}/".format(protocol, host, port, web_root, apikey)
        if section == "Radarr":
            base_url = "{0}{1}:{2}{3}/api/command".format(protocol, host, port, web_root)
            url2 = "{0}{1}:{2}{3}/api/config/downloadClient".format(protocol, host, port, web_root)
            headers = {'X-Api-Key': apikey}
        if not apikey:
            logger.info('No CouchPotato or Radarr apikey entered. Performing transcoder functions only')
            release = None
        elif server_responding(base_url):
            if section == "CouchPotato":
                release = self.get_release(base_url, imdbid, download_id)
            else:
                release = None
        else:
            logger.error("Server did not respond. Exiting", section)
            return [1, "{0}: Failed to post-process - {1} did not respond.".format(section, section)]

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
            except:
                pass

        if not os.path.isdir(dir_name) and os.path.isfile(dir_name):  # If the input directory is a file, assume single file download and split dir/name.
            dir_name = os.path.split(os.path.normpath(dir_name))[0]

        specific_path = os.path.join(dir_name, str(input_name))
        clean_name = os.path.splitext(specific_path)
        if clean_name[1] == ".nzb":
            specific_path = clean_name[0]
        if os.path.isdir(specific_path):
            dir_name = specific_path

        process_all_exceptions(input_name, dir_name)
        input_name, dir_name = convert_to_ascii(input_name, dir_name)

        if not list_media_files(dir_name, media=True, audio=False, meta=False, archives=False) and list_media_files(dir_name, media=False, audio=False, meta=False, archives=True) and extract:
            logger.debug('Checking for archives to extract in directory: {0}'.format(dir_name))
            core.extract_files(dir_name)
            input_name, dir_name = convert_to_ascii(input_name, dir_name)

        good_files = 0
        num_files = 0
        # Check video files for corruption
        for video in list_media_files(dir_name, media=True, audio=False, meta=False, archives=False):
            num_files += 1
            if transcoder.is_video_good(video, status):
                import_subs(video)
                good_files += 1
        if num_files and good_files == num_files:
            if status:
                logger.info("Status shown as failed from Downloader, but {0} valid video files found. Setting as success.".format(good_files), section)
                status = 0
        elif num_files and good_files < num_files:
            logger.info("Status shown as success from Downloader, but corrupt video files found. Setting as failed.", section)
            if 'NZBOP_VERSION' in os.environ and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
                print('[NZB] MARK=BAD')
            if failure_link:
                failure_link += '&corrupt=true'
            status = 1
        elif client_agent == "manual":
            logger.warning("No media files found in directory {0} to manually process.".format(dir_name), section)
            return [0, ""]  # Success (as far as this script is concerned)
        else:
            logger.warning("No media files found in directory {0}. Processing this as a failed download".format(dir_name), section)
            status = 1
            if 'NZBOP_VERSION' in os.environ and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
                print('[NZB] MARK=BAD')

        if status == 0:
            if core.TRANSCODE == 1:
                result, new_dir_name = transcoder.transcode_directory(dir_name)
                if result == 0:
                    logger.debug("Transcoding succeeded for files in {0}".format(dir_name), section)
                    dir_name = new_dir_name

                    chmod_directory = int(str(cfg.get("chmodDirectory", "0")), 8)
                    logger.debug("Config setting 'chmodDirectory' currently set to {0}".format(oct(chmod_directory)), section)
                    if chmod_directory:
                        logger.info("Attempting to set the octal permission of '{0}' on directory '{1}'".format(oct(chmod_directory), dir_name), section)
                        core.rchmod(dir_name, chmod_directory)
                else:
                    logger.error("Transcoding failed for files in {0}".format(dir_name), section)
                    return [1, "{0}: Failed to post-process - Transcoding failed".format(section)]
            for video in list_media_files(dir_name, media=True, audio=False, meta=False, archives=False):
                if not release and ".cp(tt" not in video and imdbid:
                    video_name, video_ext = os.path.splitext(video)
                    video2 = "{0}.cp({1}){2}".format(video_name, imdbid, video_ext)
                    if not (client_agent in [core.TORRENT_CLIENTAGENT, 'manual'] and core.USELINK == 'move-sym'):
                        logger.debug('Renaming: {0} to: {1}'.format(video, video2))
                        os.rename(video, video2)

            if not apikey:  # If only using Transcoder functions, exit here.
                logger.info('No CouchPotato or Radarr apikey entered. Processing completed.')
                return [0, "{0}: Successfully post-processed {1}".format(section, input_name)]

            params = {}
            if download_id and release_id:
                params['downloader'] = downloader or client_agent
                params['download_id'] = download_id

            params['media_folder'] = remote_dir(dir_name) if remote_path else dir_name

            if section == "CouchPotato": 
                if method == "manage":
                    command = "manage.update"
                    params = {}
                else:
                    command = "renamer.scan"

                url = "{0}{1}".format(base_url, command)
                logger.debug("Opening URL: {0} with PARAMS: {1}".format(url, params), section)
                logger.postprocess("Starting {0} scan for {1}".format(method, input_name), section)

            if section == "Radarr":
                payload = {'name': 'DownloadedMoviesScan', 'path': params['media_folder'], 'downloadClientId': download_id, 'importMode': import_mode}
                if not download_id:
                    payload.pop("downloadClientId")
                logger.debug("Opening URL: {0} with PARAMS: {1}".format(base_url, payload), section)
                logger.postprocess("Starting DownloadedMoviesScan scan for {0}".format(input_name), section)

            try:
                if section == "CouchPotato":
                    r = requests.get(url, params=params, verify=False, timeout=(30, 1800))
                else:
                    r = requests.post(base_url, data=json.dumps(payload), headers=headers, stream=True, verify=False, timeout=(30, 1800))
            except requests.ConnectionError:
                logger.error("Unable to open URL", section)
                return [1, "{0}: Failed to post-process - Unable to connect to {1}".format(section, section)]

            result = r.json()
            if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                logger.error("Server returned status {0}".format(r.status_code), section)
                return [1, "{0}: Failed to post-process - Server returned status {1}".format(section, r.status_code)]
            elif section == "CouchPotato" and result['success']:
                logger.postprocess("SUCCESS: Finished {0} scan for folder {1}".format(method, dir_name), section)
                if method == "manage":
                    return [0, "{0}: Successfully post-processed {1}".format(section, input_name)]
            elif section == "Radarr":
                logger.postprocess("Radarr response: {0}".format(result['state']))
                try:
                    res = json.loads(r.content)
                    scan_id = int(res['id'])
                    logger.debug("Scan started with id: {0}".format(scan_id), section)
                    started = True
                except Exception as e:
                    logger.warning("No scan id was returned due to: {0}".format(e), section)
                    scan_id = None
            else:
                logger.error("FAILED: {0} scan was unable to finish for folder {1}. exiting!".format(method, dir_name),
                             section)
                return [1, "{0}: Failed to post-process - Server did not return success".format(section)]

        else:
            core.FAILED = True
            logger.postprocess("FAILED DOWNLOAD DETECTED FOR {0}".format(input_name), section)
            if failure_link:
                report_nzb(failure_link, client_agent)

            if section == "Radarr":
                logger.postprocess("FAILED: The download failed. Sending failed download to {0} for CDH processing".format(section), section)
                return [1, "{0}: Download Failed. Sending back to {1}".format(section, section)]  # Return as failed to flag this in the downloader.

            if delete_failed and os.path.isdir(dir_name) and not os.path.dirname(dir_name) == dir_name:
                logger.postprocess("Deleting failed files and folder {0}".format(dir_name), section)
                remove_dir(dir_name)

            if not release_id and not media_id:
                logger.error("Could not find a downloaded movie in the database matching {0}, exiting!".format(input_name),
                             section)
                return [1, "{0}: Failed to post-process - Failed download not found in {1}".format(section, section)]

            if release_id:
                logger.postprocess("Setting failed release {0} to ignored ...".format(input_name), section)

                url = "{url}release.ignore".format(url=base_url)
                params = {'id': release_id}

                logger.debug("Opening URL: {0} with PARAMS: {1}".format(url, params), section)

                try:
                    r = requests.get(url, params=params, verify=False, timeout=(30, 120))
                except requests.ConnectionError:
                    logger.error("Unable to open URL {0}".format(url), section)
                    return [1, "{0}: Failed to post-process - Unable to connect to {1}".format(section, section)]

                result = r.json()
                if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                    logger.error("Server returned status {0}".format(r.status_code), section)
                    return [1, "{0}: Failed to post-process - Server returned status {1}".format(section, r.status_code)]
                elif result['success']:
                    logger.postprocess("SUCCESS: {0} has been set to ignored ...".format(input_name), section)
                else:
                    logger.warning("FAILED: Unable to set {0} to ignored!".format(input_name), section)
                    return [1, "{0}: Failed to post-process - Unable to set {1} to ignored".format(section, input_name)]

            logger.postprocess("Trying to snatch the next highest ranked release.", section)

            url = "{0}movie.searcher.try_next".format(base_url)
            logger.debug("Opening URL: {0}".format(url), section)

            try:
                r = requests.get(url, params={'media_id': media_id}, verify=False, timeout=(30, 600))
            except requests.ConnectionError:
                logger.error("Unable to open URL {0}".format(url), section)
                return [1, "{0}: Failed to post-process - Unable to connect to {1}".format(section, section)]

            result = r.json()
            if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                logger.error("Server returned status {0}".format(r.status_code), section)
                return [1, "{0}: Failed to post-process - Server returned status {1}".format(section, r.status_code)]
            elif result['success']:
                logger.postprocess("SUCCESS: Snatched the next highest release ...", section)
                return [0, "{0}: Successfully snatched next highest release".format(section)]
            else:
                logger.postprocess("SUCCESS: Unable to find a new release to snatch now. CP will keep searching!", section)
                return [0, "{0}: No new release found now. {1} will keep searching".format(section, section)]

        # Added a release that was not in the wanted list so confirm rename successful by finding this movie media.list.
        if not release:
            download_id = None  # we don't want to filter new releases based on this.

        # we will now check to see if CPS has finished renaming before returning to TorrentToMedia and unpausing.
        timeout = time.time() + 60 * wait_for
        while time.time() < timeout:  # only wait 2 (default) minutes, then return.
            logger.postprocess("Checking for status change, please stand by ...", section)
            if section == "CouchPotato":
                release = self.get_release(base_url, imdbid, download_id, release_id)
                scan_id = None
            else:
                release = None
            if release:
                try:
                    release_id = list(release.keys())[0]
                    title = release[release_id]['title']
                    release_status_new = release[release_id]['status']
                    if release_status_old is None:  # we didn't have a release before, but now we do.
                        logger.postprocess("SUCCESS: Movie {0} has now been added to CouchPotato with release status of [{1}]".format(
                            title, str(release_status_new).upper()), section)
                        return [0, "{0}: Successfully post-processed {1}".format(section, input_name)]

                    if release_status_new != release_status_old:
                        logger.postprocess("SUCCESS: Release for {0} has now been marked with a status of [{1}]".format(
                            title, str(release_status_new).upper()), section)
                        return [0, "{0}: Successfully post-processed {1}".format(section, input_name)]
                except:
                    pass
            elif scan_id:
                    url = "{0}/{1}".format(base_url, scan_id)
                    command_status = self.command_complete(url, params, headers, section)
                    if command_status:
                        logger.debug("The Scan command return status: {0}".format(command_status), section)
                        if command_status in ['completed']:
                            logger.debug("The Scan command has completed successfully. Renaming was successful.", section)
                            return [0, "{0}: Successfully post-processed {1}".format(section, input_name)]
                        elif command_status in ['failed']:
                            logger.debug("The Scan command has failed. Renaming was not successful.", section)
                            # return [1, "%s: Failed to post-process %s" % (section, input_name) ]

            if not os.path.isdir(dir_name):
                logger.postprocess("SUCCESS: Input Directory [{0}] has been processed and removed".format(
                    dir_name), section)
                return [0, "{0}: Successfully post-processed {1}".format(section, input_name)]

            elif not list_media_files(dir_name, media=True, audio=False, meta=False, archives=True):
                logger.postprocess("SUCCESS: Input Directory [{0}] has no remaining media files. This has been fully processed.".format(
                    dir_name), section)
                return [0, "{0}: Successfully post-processed {1}".format(section, input_name)]

            # pause and let CouchPotatoServer/Radarr catch its breath
            time.sleep(10 * wait_for)

        # The status hasn't changed. we have waited wait_for minutes which is more than enough. uTorrent can resume seeding now.
        if section == "Radarr" and self.completed_download_handling(url2, headers, section=section):
            logger.debug("The Scan command did not return status completed, but complete Download Handling is enabled. Passing back to {0}.".format(section), section)
            return [status, "{0}: Complete DownLoad Handling is enabled. Passing back to {1}".format(section, section)]
        logger.warning(
            "{0} does not appear to have changed status after {1} minutes, Please check your logs.".format(input_name, wait_for),
            section)
        return [1, "{0}: Failed to post-process - No change in status".format(section)]

    def command_complete(self, url, params, headers, section):
        try:
            r = requests.get(url, params=params, headers=headers, stream=True, verify=False, timeout=(30, 60))
        except requests.ConnectionError:
            logger.error("Unable to open URL: {0}".format(url), section)
            return None
        if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status {0}".format(r.status_code), section)
            return None
        else:
            try:
                return r.json()['state']
            except (ValueError, KeyError):
                # ValueError catches simplejson's JSONDecodeError and json's ValueError
                logger.error("{0} did not return expected json data.".format(section), section)
                return None

    def completed_download_handling(self, url2, headers, section="MAIN"):
        try:
            r = requests.get(url2, params={}, headers=headers, stream=True, verify=False, timeout=(30, 60))
        except requests.ConnectionError:
            logger.error("Unable to open URL: {0}".format(url2), section)
            return False
        if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status {0}".format(r.status_code), section)
            return False
        else:
            try:
                return r.json().get("enableCompletedDownloadHandling", False)
            except ValueError:
                # ValueError catches simplejson's JSONDecodeError and json's ValueError
                return False

    def get_release(self, base_url, imdb_id=None, download_id=None, release_id=None):
        results = {}
        params = {}

        # determine cmd and params to send to CouchPotato to get our results
        section = 'movies'
        cmd = "media.list"
        if release_id or imdb_id:
            section = 'media'
            cmd = "media.get"
            params['id'] = release_id or imdb_id

        if not (release_id or imdb_id or download_id):
            logger.debug("No information available to filter CP results")
            return results

        url = "{0}{1}".format(base_url, cmd)
        logger.debug("Opening URL: {0} with PARAMS: {1}".format(url, params))

        try:
            r = requests.get(url, params=params, verify=False, timeout=(30, 60))
        except requests.ConnectionError:
            logger.error("Unable to open URL {0}".format(url))
            return results

        try:
            result = r.json()
        except ValueError:
            # ValueError catches simplejson's JSONDecodeError and json's ValueError
            logger.error("CouchPotato returned the following non-json data")
            for line in r.iter_lines():
                logger.error("{0}".format(line))
            return results

        if not result['success']:
            if 'error' in result:
                logger.error('{0}'.format(result['error']))
            else:
                logger.error("no media found for id {0}".format(params['id']))
            return results

        # Gather release info and return it back, no need to narrow results
        if release_id:
            try:
                id = result[section]['_id']
                results[id] = result[section]
                return results
            except:
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

                    id = release['_id']
                    results[id] = release
                    results[id]['title'] = movie['title']
                except:
                    continue

        # Narrow results by removing old releases by comparing their last_edit field
        if len(results) > 1:
            for id1, x1 in results.items():
                for id2, x2 in results.items():
                    try:
                        if x2["last_edit"] > x1["last_edit"]:
                            results.pop(id1)
                    except:
                        continue

        # Search downloads on clients for a match to try and narrow our results down to 1
        if len(results) > 1:
            for id, x in results.items():
                try:
                    if not find_download(str(x['download_info']['downloader']).lower(), x['download_info']['id']):
                        results.pop(id)
                except:
                    continue

        return results
