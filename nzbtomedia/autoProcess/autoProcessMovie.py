import os
import time
import nzbtomedia
from lib import requests
from nzbtomedia.Transcoder import Transcoder
from nzbtomedia.nzbToMediaSceneExceptions import process_all_exceptions
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, delete, find_imdbid, find_download
from nzbtomedia import logger


class autoProcessMovie:
    def get_releases(self, baseURL, imdbid=None, download_id=None):
        results = {}
        params = {}

        # determin cmd and params to send to CouchPotato to get our results
        section = 'movies'
        cmd = "/media.list"
        if imdbid:
            section = 'media'
            cmd = "/media.get"
            params['id'] = imdbid

        url = baseURL + cmd
        logger.debug("Opening URL: %s" % url)

        try:
            r = requests.get(url, params=params)
        except requests.ConnectionError:
            logger.error("Unable to open URL %s" % url)
            return

        result = r.json()
        movies = result[section]
        if not isinstance(movies, list):
            movies = [movies]
        for movie in movies:
            if movie['status'] not in ['active', 'done']:
                continue
            releases = movie['releases']
            for release in releases:
                if release['status'] not in ['snatched', 'done']:
                    continue
                try:
                    if download_id:
                        if download_id != release['download_info']['id']:
                            continue

                    id = release['_id']
                    results[id] = release
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

    def releases_diff(self, dict_a, dict_b):
        return dict([
            (key, dict_b.get(key, dict_a.get(key)))
            for key in set(dict_a.keys() + dict_b.keys())
            if (
                (key in dict_a and (not key in dict_b or dict_a[key] != dict_b[key])) or
                (key in dict_b and (not key in dict_a or dict_a[key] != dict_b[key]))
            )
        ])

    def process(self, dirName, nzbName=None, status=0, clientAgent="manual", download_id="", inputCategory=None):
        # auto-detect correct section
        section = nzbtomedia.CFG.findsection(inputCategory)
        if not section:
            logger.error(
                "We were unable to find a section for category %s, please check your autoProcessMedia.cfg file." % inputCategory)
            return 1

        status = int(status)

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
        releases = self.get_releases(baseURL, imdbid, download_id)

        # pull info from release found if available
        release_id = None
        media_id = None
        downloader = None
        if len(releases) == 1:
            try:
                release_id = releases.keys()[0]
                media_id = releases[release_id]['media_id']
                download_id = releases[release_id]['download_info']['id']
                downloader = releases[release_id]['download_info']['downloader']
            except:
                pass

        process_all_exceptions(nzbName.lower(), dirName)
        nzbName, dirName = convert_to_ascii(nzbName, dirName)

        if status == 0:
            if nzbtomedia.TRANSCODE == 1:
                result = Transcoder().Transcode_directory(dirName)
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
                dirName_new = os.path.join(remote_path, os.path.basename(dirName)).replace("\\", "/")
                params['media_folder'] = dirName_new

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

        else:
            logger.postprocess("FAILED DOWNLOAD DETECTED FOR %s" % (nzbName), section)

            if delete_failed and os.path.isdir(dirName) and not os.path.dirname(dirName) == dirName:
                logger.postprocess("Deleting failed files and folder %s" % dirName, section)
                delete(dirName)

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
            releases_current = self.get_releases(baseURL, imdbid, download_id)
            logger.postprocess("Checking for status change, please stand by ...", section)
            if len(releases) > len(releases_current):  # Something has changed. CPS must have processed this movie.
                try:
                    release_status = releases_current['status']
                    logger.postprocess("SUCCESS: Release %s has now been marked with a status of [%s]" % (
                        nzbName, str(release_status).upper()), section)
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