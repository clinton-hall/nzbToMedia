import os
import re
import time
import nzbtomedia
from lib import requests
from nzbtomedia.Transcoder import Transcoder
from nzbtomedia.nzbToMediaSceneExceptions import process_all_exceptions
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, delete, create_torrent_class, clean_nzbname
from nzbtomedia import logger

class autoProcessMovie:
    def find_imdbid(self, dirName, nzbName):
        nzbName = clean_nzbname(nzbName)
        # find imdbid in dirName
        m = re.search('(tt\d{7})', dirName)
        if m:
            imdbid = m.group(1)
            logger.postprocess("Found movie id %s in directory", imdbid)
            return imdbid

        # find imdbid in nzbName
        m = re.search('(tt\d{7})', nzbName)
        if m:
            imdbid = m.group(1)
            logger.postprocess("Found imdbid %s in name", imdbid)
            return imdbid

        m = re.search("^(.+)\W(\d{4})", os.path.basename(dirName))
        if m:
            title = m.group(1)
            year = m.group(2)

            url = "http://www.omdbapi.com"

            logger.debug("Opening URL: %s", url)

            try:
                r = requests.get(url, params={'y':year, 't':title})
            except requests.ConnectionError:
                logger.error("Unable to open URL")
                return

            results = r.json()
            if hasattr(results, 'imdbID'):
                return results['imdbID']

    def get_releases(self, baseURL, download_id, dirName, nzbName):
        releases = {}
        params = {}

        imdbid = self.find_imdbid(dirName, nzbName)

        # determin cmd and params to send to CouchPotato to get our results
        section = 'movies'
        cmd = "/media.list"
        params['status'] = 'active,done'
        if imdbid:
            section = 'media'
            cmd = "/media.get"
            params['id'] = imdbid
        if download_id:
            params['release_status'] = 'snatched,downloaded'

        url = baseURL + cmd
        logger.debug("Opening URL: %s", url)

        try:
            r = requests.get(url, params=params)
        except requests.ConnectionError:
            logger.error("Unable to open URL")
            return

        results = r.json()

        movies = results[section]
        if not isinstance(movies, list):
            movies = [movies]

        for movie in movies:
            for release in movie['releases']:
                if download_id:
                    try:
                        if download_id != release['download_info']['id']:
                                continue
                    except:continue

                id = release['_id']
                releases[id] = release

        return releases

    def releases_diff(self, dict_a, dict_b):
        return dict([
            (key, dict_b.get(key, dict_a.get(key)))
            for key in set(dict_a.keys() + dict_b.keys())
            if (
                (key in dict_a and (not key in dict_b or dict_a[key] != dict_b[key])) or
                (key in dict_b and (not key in dict_a or dict_a[key] != dict_b[key]))
            )
        ])

    def process(self, dirName, nzbName=None, status=0, clientAgent = "manual", download_id = "", inputCategory=None):
        if dirName is None:
            logger.error("No directory was given!")
            return 1  # failure

        # auto-detect correct section
        section = nzbtomedia.CFG.findsection(inputCategory)
        if not section:
            logger.error(
                "We were unable to find a section for category %s, please check your autoProcessMedia.cfg file.", inputCategory)
            return 1

        logger.postprocess("#########################################################")
        logger.postprocess("## ..::[%s]::.. :: CATEGORY:[%s]", section, inputCategory)
        logger.postprocess("#########################################################")

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
            transcode = int(nzbtomedia.CFG["Transcoder"]["transcode"])
        except:
            transcode = 0
        try:
            remote_path = nzbtomedia.CFG[section][inputCategory]["remote_path"]
        except:
            remote_path = None

        nzbName = str(nzbName) # make sure it is a string

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        baseURL = "%s%s:%s%s/api/%s" % (protocol, host, port, web_root, apikey)

        releases = self.get_releases(baseURL, download_id, dirName, nzbName)

        if not releases:
            logger.error("Could not find any releases marked as WANTED on CouchPotato to compare changes against %s, skipping ...", nzbName)
            return 1

        # try to get release_id, media_id, and download_id if one was not passed in
        release_id = None
        media_id = None
        if len(releases) == 1:
            try:
                release_id = releases.keys()[0]
                media_id = releases[release_id]['media_id']
                download_id = releases['download_info']['id']
            except:pass

        process_all_exceptions(nzbName.lower(), dirName)
        nzbName, dirName = convert_to_ascii(nzbName, dirName)

        if status == 0:
            if transcode == 1:
                result = Transcoder().Transcode_directory(dirName)
                if result == 0:
                    logger.debug("Transcoding succeeded for files in %s", dirName)
                else:
                    logger.warning("Transcoding failed for files in %s", dirName)

            if method == "manage":
                command = "/manage.update"
            else:
                command = "/renamer.scan"

            params = {}
            if download_id:
                params['downloader'] = clientAgent
                params['download_id'] = download_id

            params['media_folder'] = dirName
            if remote_path:
                dirName_new = os.path.join(remote_path, os.path.basename(dirName)).replace("\\", "/")
                params['media_folder'] = dirName_new

            url = baseURL + command

            logger.debug("Opening URL: %s", url)

            logger.postprocess("Attempting to perform a %s scan on CouchPotato for %s", method, nzbName)

            try:
                r = requests.get(url, params=params)
            except requests.ConnectionError:
                logger.error("Unable to open URL")
                return 1 # failure

            result = r.json()
            if result['success']:
                logger.postprocess("SUCCESS: %s scan started on CouchPotatoServer for %s", method, nzbName)
            else:
                logger.error("FAILED: %s scan has NOT started on CouchPotato for %s. Exiting ...", method, nzbName)
                return 1 # failure

        else:
            logger.postprocess("Download of %s has failed.", nzbName)

            if delete_failed and os.path.isdir(dirName) and not os.path.dirname(dirName) == dirName:
                logger.postprocess("Deleting failed files and folder %s", dirName)
                delete(dirName)

            if not download_id:
                logger.warning("Could not find a movie in the database for release %s", nzbName)
                logger.warning("Please manually ignore this release and refresh the wanted movie from CouchPotato, Exiting ...")
                return 1 # failure

            logger.postprocess("Ignoring current failed release %s ...", nzbName)

            url = baseURL + "/release.ignore"
            logger.debug("Opening URL: %s", url)

            try:
                r = requests.get(url, params={'id': release_id})
            except requests.ConnectionError:
                logger.error("Unable to open URL")
                return 1  # failure

            result = r.json()
            if result['success']:
                logger.postprocess("%s has been set to ignored on CouchPotato", nzbName)
            else:
                logger.warning("Failed to ignore %s on CouchPotato ...", nzbName)

            logger.postprocess("Snatching next highest ranked release on CouchPotato ...")

            url = baseURL + "/movie.searcher.try_next"
            logger.debug("Opening URL: %s", url)

            try:
                r = requests.get(url, params={'media_id': media_id})
            except requests.ConnectionError:
                logger.error("Unable to open URL")
                return 1  # failure

            result = r.json()
            if result['success']:
                logger.postprocess("CouchPotato successfully snatched the next highest release above %s ...", nzbName)
                return 0
            else:
                logger.postprocess("CouchPotato was unable to find a higher release then %s to snatch ...", nzbName)
                return 1

        # we will now check to see if CPS has finished renaming before returning to TorrentToMedia and unpausing.
        timeout = time.time() + 60 * wait_for
        while (time.time() < timeout):  # only wait 2 (default) minutes, then return.
            releases_current = self.get_releases(baseURL, download_id, dirName, nzbName)
            releasesDiff = self.releases_diff(releases, releases_current)
            if releasesDiff:  # Something has changed. CPS must have processed this movie.
                release_status = releasesDiff[releasesDiff.keys()[0]]['status']
                logger.postprocess("SUCCESS: Release %s marked as [%s] on CouchPotato", nzbName, release_status)
                return 0 # success

            # pause and let CouchPotatoServer catch its breath
            time.sleep(10 * wait_for)

        # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resule seeding now.
        logger.warning("The movie does not appear to have changed status after %s minutes. Please check CouchPotato Logs", wait_for)
        return 1 # failure