import os
import time

import nzbtomedia
from lib import requests
from nzbtomedia.nzbToMediaSceneExceptions import process_all_exceptions
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, rmDir, find_imdbid, find_download, joinPath, listMediaFiles
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
        logger.debug("Opening URL: %s" % url)

        try:
            r = requests.get(url, params=params)
        except requests.ConnectionError:
            logger.error("Unable to open URL %s" % url)
            return

        result = r.json()
        if not result['success']:
            logger.error(str(result['error']))
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

        # Narrow results by removing old releases by comparing there last_edit field
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

    def process(self, dirName, nzbName=None, status=0, clientAgent="manual", download_id="", inputCategory=None):
        # auto-detect correct section
        section = nzbtomedia.CFG.findsection(inputCategory)
        if not section:
            logger.error(
                "We were unable to find a section for category %s, please check your autoProcessMedia.cfg file." % inputCategory)
            return 1

        # Check video files for corruption
        status = int(status)
        for video in listMediaFiles(dirName):
            if not transcoder.isVideoGood(video):
                status = 1

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
            remote_path = nzbtomedia.CFG[section][inputCategory]["remote_path"]
        except:
            remote_path = None

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        baseURL = "%s%s:%s%s/api/%s" % (protocol, host, port, web_root, apikey)

        imdbid = find_imdbid(dirName, nzbName)
        release = self.get_release(baseURL, imdbid, download_id)

        # pull info from release found if available
        release_id = None
        media_id = None
        downloader = None
        release_status_old = None
        if len(release) == 1:
            try:
                release_id = release.keys()[0]
                media_id = release[release_id]['media_id']
                download_id = release[release_id]['download_info']['id']
                downloader = release[release_id]['download_info']['downloader']
                release_status_old = release[release_id]['status']
            except:
                pass

        process_all_exceptions(nzbName.lower(), dirName)
        nzbName, dirName = convert_to_ascii(nzbName, dirName)

        if status == 0:
            if nzbtomedia.TRANSCODE == 1:
                result = transcoder.Transcode_directory(dirName)
                if result == 0:
                    logger.debug("Transcoding succeeded for files in %s" % (dirName), section)
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
                params['media_folder'] = joinPath(remote_path, os.path.basename(dirName))

            url = "%s%s" % (baseURL, command)

            logger.debug("Opening URL: %s" % (url), section)

            logger.postprocess("Starting %s scan for %s" % (method, nzbName), section)

            try:
                r = requests.get(url, params=params)
            except requests.ConnectionError:
                logger.error("Unable to open URL", section)
                return 1  # failure

            result = r.json()
            if result['success']:
                logger.postprocess("SUCCESS: Finished %s scan for folder %s" % (method, dirName), section)
            else:
                logger.error("FAILED: %s scan was unable to finish for folder %s. exiting!" % (method, dirName),
                             section)
                return 1  # failure

            # Added a releease that was not in the wanted list so no way to check status, exit without errors
            if not release:
                return 0
        else:
            logger.postprocess("FAILED DOWNLOAD DETECTED FOR %s" % (nzbName), section)

            if delete_failed and os.path.isdir(dirName) and not os.path.dirname(dirName) == dirName:
                logger.postprocess("Deleting failed files and folder %s" % dirName, section)
                rmDir(dirName)

            if not download_id:
                logger.error("Could not find a downloaded movie in the database matching %s, exiting!" % nzbName,
                             section)
                return 1  # failure

            logger.postprocess("Setting failed release %s to ignored ..." % (nzbName), section)

            url = baseURL + "/release.ignore"
            logger.debug("Opening URL: %s" % (url), section)

            try:
                r = requests.get(url, params={'id': release_id})
            except requests.ConnectionError:
                logger.error("Unable to open URL %s" % (url), section)
                return 1  # failure

            result = r.json()
            if result['success']:
                logger.postprocess("SUCCESS: %s has been set to ignored ..." % (nzbName), section)
            else:
                logger.warning("FAILED: Unable to set %s to ignored!" % (nzbName), section)

            logger.postprocess("Trying to snatch the next highest ranked release.", section)

            url = "%s/movie.searcher.try_next" % (baseURL)
            logger.debug("Opening URL: %s" % (url), section)

            try:
                r = requests.get(url, params={'media_id': media_id})
            except requests.ConnectionError:
                logger.error("Unable to open URL %s" % (url), section)
                return 1  # failure

            result = r.json()
            if result['success']:
                logger.postprocess("SUCCESS: Snatched the next highest release ...", section)
                return 0
            else:
                logger.postprocess("FAILED: Unable to find a higher ranked release then %s to snatch!" % (nzbName),
                                   section)
                return 1

        # we will now check to see if CPS has finished renaming before returning to TorrentToMedia and unpausing.
        timeout = time.time() + 60 * wait_for
        while (time.time() < timeout):  # only wait 2 (default) minutes, then return.
            logger.postprocess("Checking for status change, please stand by ...", section)
            release = self.get_release(baseURL, imdbid, download_id, release_id)
            if release:
                try:
                    release_status_new = release[release_id]['status']
                    if release_status_new != release_status_old:
                        logger.postprocess("SUCCESS: Release %s has now been marked with a status of [%s]" % (
                            nzbName, str(release_status_new).upper()), section)
                        return 0  # success
                except:
                    pass

            # pause and let CouchPotatoServer catch its breath
            time.sleep(10 * wait_for)

        # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resule seeding now.
        logger.warning(
            "%s does not appear to have changed status after %s minutes, Please check your logs." % (nzbName, wait_for),
            section)
        return 1  # failure