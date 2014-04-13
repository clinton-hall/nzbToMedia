import os
import re
import time
import datetime
import urllib
import shutil
import sys
import platform
import nzbtomedia
from lib import requests
from nzbtomedia.Transcoder import Transcoder
from nzbtomedia.nzbToMediaSceneExceptions import process_all_exceptions
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, delete, create_torrent_class
from nzbtomedia import logger
from nzbtomedia.transmissionrpc.client import Client as TransmissionClient

class autoProcessMovie:
    def find_release_info(self, baseURL, download_id, dirName, nzbName):
        def search_torrents(releases, nzbName):
            for release in releases:
                try:
                    if release['status'] != 'snatched':
                        continue

                    if download_id:
                        if download_id == release['download_info']['id']:
                            return release

                    if imdbid:
                        if imdbid == release['download_info']['id']:
                            return release

                    downloader = release['download_info']['downloader'].lower()
                    tor_client = create_torrent_class(downloader)

                    torrents = []
                    if downloader == "transmission":
                        torrents = tor_client.get_torrents()
                    elif downloader == "deluge":
                        torrents = tor_client.get_torrents()
                    elif downloader == "utorrent":
                        torrents = tor_client.get_torrents()

                    for torrent in torrents:
                        tor_name = torrent.name
                        tor_hash = torrent.hashString

                        if download_id:
                            if download_id == tor_hash:
                                return release

                        if nzbName == tor_name:
                            return release
                except:pass

        imdbid = None
        release_id = None
        media_id = None
        release_status = None
        matched_release = None
        downloader = None

        while(True):
            # find imdbid in nzbName
            a = nzbName.find('.cp(') + 4
            b = nzbName[a:].find(')') + a
            if a > 3:  # a == 3 if not exist
                if nzbName[a:b]:
                    imdbid = nzbName[a:b]
                    logger.postprocess("Found imdbid %s in name", imdbid)
                    break

            # find imdbid in dirName
            a = dirName.find('.cp(') + 4
            b = dirName[a:].find(')') + a
            if a > 3:  # a == 3 if not exist
                if dirName[a:b]:
                    imdbid = dirName[a:b]
                    logger.postprocess("Found movie id %s in directory", imdbid)
                    break
            break

        url = baseURL + "/media.list/?release_status=snatched"

        logger.debug("Opening URL: %s", url)

        try:
            r = requests.get(url)
        except requests.ConnectionError:
            logger.error("Unable to open URL")
            return

        results = r.json()
        for movie in results['movies']:
            if imdbid:
                if imdbid != movie['info']['imdb']:
                    continue
            matched_release = search_torrents(movie['releases'], nzbName)
            if matched_release:
                break

        if matched_release:
            try:
                release_id = matched_release['_id']
                media_id = matched_release['media_id']
                release_status = matched_release['status']
                download_id = matched_release['download_info']['id']
                downloader = matched_release['download_info']['downloader']
            except:pass

        return media_id, download_id, downloader, release_id, release_status

    def get_status(self, baseURL, release_id):
        release_status = None

        logger.debug("Attempting to get current status for release:%s", release_id)

        url = baseURL + "/media.get"
        logger.debug("Opening URL: %s", url)

        try:
            r = requests.get(url, params={'id':release_id})
        except requests.ConnectionError:
            logger.error("Unable to open URL")
            return None, None

        try:
            result = r.json()
            release_status = result["media"]["status"]
        except:pass

        return release_status

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

        baseURL = protocol + host + ":" + port + web_root + "/api/" + apikey

        media_id, download_id, downloader, release_id, release_status = self.find_release_info(baseURL, download_id, dirName, nzbName) # get the CPS database movie id for this movie.

        if release_status is None:
            logger.error("Could not find a current status for %s on CouchPotatoServer", nzbName)
            return 1

        # failed to get a download id
        if release_status != "snatched":
            logger.postprocess("%s has is marked with a status of [%s] by CouchPotatoServer, skipping ...", nzbName, release_status.upper())
            return 0

        if not download_id:
            logger.warning("Could not find a download ID in CouchPotatoServer database for release %s, skipping", nzbName)
            logger.warning("Please manually ignore this release and try snatching it again")
            return 1  # failure

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
                if downloader:
                    params['downloader'] = downloader or clientAgent
                params['download_id'] = download_id

            if remote_path:
                dirName_new = os.path.join(remote_path, os.path.basename(dirName)).replace("\\", "/")
                params['media_folder'] = urllib.quote(dirName_new)

            url = baseURL + command

            logger.debug("Opening URL: %s", url)

            try:
                r = requests.get(url, params=params)
            except requests.ConnectionError:
                logger.error("Unable to open URL")
                return 1 # failure

            result = r.json()
            logger.postprocess("CouchPotatoServer returned %s", result)
            if result['success']:
                logger.postprocess("%s scan started on CouchPotatoServer for %s", method, nzbName)
            else:
                logger.error("%s scan has NOT started on CouchPotatoServer for %s. Exiting", method, nzbName)
                return 1 # failure

        else:
            logger.postprocess("Download of %s has failed.", nzbName)
            logger.postprocess("Trying to re-cue the next highest ranked release")

            if not download_id:
                logger.warning("Cound not find a movie in the database for release %s", nzbName)
                logger.warning("Please manually ignore this release and refresh the wanted movie")
                logger.error("Exiting autoProcessMovie script")
                return 1 # failure

            url = baseURL + "movie.searcher.try_next/?media_id=" + media_id

            logger.debug("Opening URL: %s", url)

            try:
                r = requests.get(url, stream=True)
            except requests.ConnectionError:
                logger.error("Unable to open URL")
                return 1  # failure

            for line in r.iter_lines():
                if line: logger.postprocess("%s", line)

            logger.postprocess("%s FAILED!, Trying the next best release on CouchPotatoServer", nzbName)
            if delete_failed and not os.path.dirname(dirName) == dirName:
                logger.postprocess("Deleting failed files and folder %s", dirName)
                delete(dirName)
            return 0 # success

        if not download_id or not release_id:
            if clientAgent in ['utorrent', 'transmission', 'deluge'] :
                return 1 # just to be sure TorrentToMedia doesn't start deleting files as we havent verified changed status.
            else:
                return 0  # success

        # we will now check to see if CPS has finished renaming before returning to TorrentToMedia and unpausing.
        timeout = time.time() + 60 * int(wait_for)
        while (True):  # only wait 2 (default) minutes, then return.
            if time.time() > timeout:
                break

            current_status = self.get_status(baseURL, release_id)
            if current_status is None:
                logger.error("Could not find a current status for %s on CouchPotatoServer", nzbName)
                return 1

            if current_status != release_status:  # Something has changed. CPS must have processed this movie.
                logger.postprocess("SUCCESS: This release is now marked as status [%s] in CouchPotatoServer", current_status.upper())
                return 0 # success

        # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resule seeding now.
        logger.warning("The movie does not appear to have changed status after %s minutes. Please check CouchPotato Logs", wait_for)
        return 1 # failure