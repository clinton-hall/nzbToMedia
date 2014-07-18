import os
import time
import requests
import nzbtomedia

from nzbtomedia.nzbToMediaSceneExceptions import process_all_exceptions
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, rmDir, find_imdbid, find_download, listMediaFiles, remoteDir, import_subs, server_responding
from nzbtomedia import logger
from nzbtomedia.transcoder import transcoder


class autoProcessMovie:
    def get_release(self, baseURL, imdbid=None, download_id=None, release_id=None):
        results = {}
        params = {}

        # determin cmd and params to send to CouchPotato to get our results
        section = 'movies'
        cmd = "/media.list"
        if release_id or imdbid:
            section = 'media'
            cmd = "/media.get"
            params['id'] = release_id or imdbid

        url = baseURL + cmd
        logger.debug("Opening URL: %s with PARAMS: %s" % (url, params))

        try:
            r = requests.get(url, params=params, verify=False)
        except requests.ConnectionError:
            logger.error("Unable to open URL %s" % url)
            return results

        try:
            result = r.json()
        except:
            logger.error("CouchPotato returned the following non-json data")
            for line in r.iter_lines():
                logger.error("%s" %(line))
            return results

        if not result['success']:
            if 'error' in result:
                logger.error(str(result['error']))
            else:
                logger.error("no media found for id %s" % (params['id'])) 
            return results

        # Gather release info and return it back, no need to narrow results
        if release_id:
            try:
                id = result[section]['_id']
                results[id] = result[section]
                return results
            except:pass

        # Gather release info and proceed with trying to narrow results to one release choice

        movies = result[section]
        if not isinstance(movies, list):
            movies = [movies]
        for movie in movies:
            if movie['status'] not in ['active', 'done']:
                continue
            releases = movie['releases']
            for release in releases:
                try:
                    if release['status'] not in ['snatched', 'downloaded', 'done']:
                        continue
                    if download_id:
                        if download_id != release['download_info']['id']:
                            continue

                    id = release['_id']
                    results[id] = release
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

    def process(self, section, dirName, inputName=None, status=0, clientAgent="manual", download_id="", inputCategory=None):

        host = nzbtomedia.CFG[section][inputCategory]["host"]
        port = nzbtomedia.CFG[section][inputCategory]["port"]
        apikey = nzbtomedia.CFG[section][inputCategory]["apikey"]
        method = nzbtomedia.CFG[section][inputCategory]["method"]
        delete_failed = int(nzbtomedia.CFG[section][inputCategory]["delete_failed"])
        wait_for = int(nzbtomedia.CFG[section][inputCategory]["wait_for"])

        try:
            ssl = int(nzbtomedia.CFG[section][inputCategory]["ssl"])
        except:
            ssl = 0
        try:
            web_root = nzbtomedia.CFG[section][inputCategory]["web_root"]
        except:
            web_root = ""
        try:
            remote_path = int(nzbtomedia.CFG[section][inputCategory]["remote_path"])
        except:
            remote_path = 0

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        baseURL = "%s%s:%s%s/api/%s" % (protocol, host, port, web_root, apikey)
        if not server_responding(baseURL):
            logger.error("Server did not respond. Exiting", section)
            return [1, "%s: Failed to post-process - %s did not respond." % (section, section) ]

        imdbid = find_imdbid(dirName, inputName)
        release = self.get_release(baseURL, imdbid, download_id)

        # pull info from release found if available
        release_id = None
        media_id = None
        downloader = None
        release_status_old = None
        if release:
            try:
                release_id = release.keys()[0]
                media_id = release[release_id]['media_id']
                download_id = release[release_id]['download_info']['id']
                downloader = release[release_id]['download_info']['downloader']
                release_status_old = release[release_id]['status']
            except:
                pass

        if not os.path.isdir(dirName) and os.path.isfile(dirName): # If the input directory is a file, assume single file download and split dir/name.
            dirName = os.path.split(os.path.normpath(dirName))[0]

        SpecificPath = os.path.join(dirName, str(inputName))
        cleanName = os.path.splitext(SpecificPath)
        if cleanName[1] == ".nzb":
            SpecificPath = cleanName[0]
        if os.path.isdir(SpecificPath):
            dirName = SpecificPath

        process_all_exceptions(inputName.lower(), dirName)
        inputName, dirName = convert_to_ascii(inputName, dirName)

        if not listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False) and listMediaFiles(dirName, media=False, audio=False, meta=False, archives=True):
            logger.debug('Checking for archives to extract in directory: %s' % (dirName))
            nzbtomedia.extractFiles(dirName)
            inputName, dirName = convert_to_ascii(inputName, dirName)

        good_files = 0
        num_files = 0
        # Check video files for corruption
        status = int(status)
        for video in listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False):
            num_files += 1
            if transcoder.isVideoGood(video, status):
                import_subs(video)
                good_files += 1
                if not release and not ".cp(tt" in video and imdbid:
                    videoName, videoExt = os.path.splitext(video)
                    video2 = "%s.cp(%s)%s" % (videoName, imdbid, videoExt)
                    logger.debug('Renaming: %s to: %s' % (video, video2))
                    os.rename(video, video2)
        if num_files > 0 and good_files == num_files:
            if status:
                logger.info("Status shown as failed from Downloader, but %s valid video files found. Setting as success." % (str(good_files)), section)
                status = 0
        elif num_files > 0 and good_files < num_files:
            logger.info("Status shown as success from Downloader, but corrupt video files found. Setting as failed.", section)
            status = 1
        elif clientAgent == "manual":
            logger.warning("No media files found in directory %s to manually process." % (dirName), section)
            return [0, ""]  # Success (as far as this script is concerned)
        else:
            logger.warning("No media files found in directory %s. Processing this as a failed download" % (dirName), section)
            status = 1

        if status == 0:
            if nzbtomedia.TRANSCODE == 1:
                result, newDirName = transcoder.Transcode_directory(dirName)
                if result == 0:
                    logger.debug("Transcoding succeeded for files in %s" % (dirName), section)
                    dirName = newDirName
                else:
                    logger.warning("Transcoding failed for files in %s" % (dirName), section)

            if method == "manage":
                command = "/manage.update"
            else:
                command = "/renamer.scan"

            params = {}
            if download_id:
                params['downloader'] = downloader or clientAgent
                params['download_id'] = download_id

            params['media_folder'] = dirName
            if remote_path:
                params['media_folder'] = remoteDir(dirName)

            url = "%s%s" % (baseURL, command)

            logger.debug("Opening URL: %s with PARAMS: %s" % (url, params), section)

            logger.postprocess("Starting %s scan for %s" % (method, inputName), section)

            try:
                r = requests.get(url, params=params, verify=False)
            except requests.ConnectionError:
                logger.error("Unable to open URL", section)
                return [1, "%s: Failed to post-process - Unable to connect to %s" % (section, section) ]

            result = r.json()
            if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                logger.error("Server returned status %s" % (str(r.status_code)), section)
                return [1, "%s: Failed to post-process - Server returned status %s" % (section, str(r.status_code)) ]
            elif result['success']:
                logger.postprocess("SUCCESS: Finished %s scan for folder %s" % (method, dirName), section)
            else:
                logger.error("FAILED: %s scan was unable to finish for folder %s. exiting!" % (method, dirName),
                             section)
                return [1, "%s: Failed to post-process - Server did not return success" % (section) ]

        else:
            logger.postprocess("FAILED DOWNLOAD DETECTED FOR %s" % (inputName), section)

            if delete_failed and os.path.isdir(dirName) and not os.path.dirname(dirName) == dirName:
                logger.postprocess("Deleting failed files and folder %s" % dirName, section)
                rmDir(dirName)

            if not download_id:
                logger.error("Could not find a downloaded movie in the database matching %s, exiting!" % inputName,
                             section)
                return [1, "%s: Failed to post-process - Failed download not found in %s" % (section, section) ]

            logger.postprocess("Setting failed release %s to ignored ..." % (inputName), section)

            url = baseURL + "/release.ignore"
            params = {'id': release_id}

            logger.debug("Opening URL: %s with PARAMS: %s" % (url, params), section)

            try:
                r = requests.get(url, params=params, verify=False)
            except requests.ConnectionError:
                logger.error("Unable to open URL %s" % (url), section)
                return [1, "%s: Failed to post-process - Unable to connect to %s" % (section, section) ]

            result = r.json()
            if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                logger.error("Server returned status %s" % (str(r.status_code)), section)
                return [1, "%s: Failed to post-process - Server returned status %s" % (section, str(r.status_code)) ]
            elif result['success']:
                logger.postprocess("SUCCESS: %s has been set to ignored ..." % (inputName), section)
            else:
                logger.warning("FAILED: Unable to set %s to ignored!" % (inputName), section)
                return [1, "%s: Failed to post-process - Unable to set %s to ignored" % (section, inputName) ]

            logger.postprocess("Trying to snatch the next highest ranked release.", section)

            url = "%s/movie.searcher.try_next" % (baseURL)
            logger.debug("Opening URL: %s" % (url), section)

            try:
                r = requests.get(url, params={'media_id': media_id})
            except requests.ConnectionError:
                logger.error("Unable to open URL %s" % (url), section)
                return [1, "%s: Failed to post-process - Unable to connect to %s" % (section, section) ]

            result = r.json()
            if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                logger.error("Server returned status %s" % (str(r.status_code)), section)
                return [1, "%s: Failed to post-process - Server returned status %s" % (section, str(r.status_code)) ]
            elif result['success']:
                logger.postprocess("SUCCESS: Snatched the next highest release ...", section)
                return [0, "%s: Successfully snatched next highest release" % (section) ]
            else:
                logger.postprocess("SUCCESS: Unable to find a new release to snatch now. CP will keep searching!", section)
                return [0, "%s: No new release found now. %s will keep searching" % (section, section) ]

        # Added a releease that was not in the wanted list so confirm rename successful by finding this movie media.list.
        if not release:
            download_id = None  # we don't want to filter new releases based on this.

        # we will now check to see if CPS has finished renaming before returning to TorrentToMedia and unpausing.
        timeout = time.time() + 60 * wait_for
        while (time.time() < timeout):  # only wait 2 (default) minutes, then return.
            logger.postprocess("Checking for status change, please stand by ...", section)
            release = self.get_release(baseURL, imdbid, download_id, release_id)
            if release:
                try:
                    if release_id is None and release_status_old is None:  # we didn't have a release before, but now we do.
                        logger.postprocess("SUCCESS: Movie %s has now been added to CouchPotato" % (imdbid), section)
                        return [0, "%s: Successfully post-processed %s" % (section, inputName) ]

                    release_status_new = release[release_id]['status']
                    if release_status_new != release_status_old:
                        logger.postprocess("SUCCESS: Release %s has now been marked with a status of [%s]" % (
                            inputName, str(release_status_new).upper()), section)
                        return [0, "%s: Successfully post-processed %s" % (section, inputName) ]
                except:
                    pass
            if not os.path.isdir(dirName):
                logger.postprocess("SUCCESS: Input Directory [%s] has been processed and removed" % (
                    dirName), section)
                return [0, "%s: Successfully post-processed %s" % (section, inputName) ]

            elif not listMediaFiles(dirName, media=True, audio=False, meta=False, archives=True):
                logger.postprocess("SUCCESS: Input Directory [%s] has no remaining media files. This has been fully processed." % (
                    dirName), section)
                return [0, "%s: Successfully post-processed %s" % (section, inputName) ]

            # pause and let CouchPotatoServer catch its breath
            time.sleep(10 * wait_for)

        # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resule seeding now.
        logger.warning(
            "%s does not appear to have changed status after %s minutes, Please check your logs." % (inputName, wait_for),
            section)
        return [1, "%s: Failed to post-process - No change in status" % (section) ]
