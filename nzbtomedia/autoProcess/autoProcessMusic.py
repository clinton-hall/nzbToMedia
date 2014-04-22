import os
import time
import nzbtomedia
from lib import requests
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, joinPath
from nzbtomedia import logger

class autoProcessMusic:
    def get_status(self, baseURL, apikey, dirName):
        logger.debug("Attempting to get current status for release:%s" % (os.path.basename(dirName)))

        url = baseURL

        params = {}
        params['apikey'] = apikey
        params['cmd'] = "getHistory"

        logger.debug("Opening URL: %s" % (url))

        try:
            r = requests.get(url, params=params)
        except requests.ConnectionError:
            logger.error("Unable to open URL")
            return None, None

        try:
            result = r.json()
            for album in result:
                if os.path.basename(dirName) == album['FolderName']:
                     return album["Status"].lower()
        except:pass

    def process(self, dirName, nzbName=None, status=0, clientAgent="manual", inputCategory=None):
        # auto-detect correct section
        section = nzbtomedia.CFG.findsection(inputCategory)
        if len(section) == 0:
            logger.error(
                "We were unable to find a section for category %s, please check your autoProcessMedia.cfg file." % (inputCategory))
            return 1

        status = int(status)

        host = nzbtomedia.CFG[section][inputCategory]["host"]
        port = nzbtomedia.CFG[section][inputCategory]["port"]
        apikey = nzbtomedia.CFG[section][inputCategory]["apikey"]
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

        nzbName, dirName = convert_to_ascii(nzbName, dirName)

        url = "%s%s:%s%s/api" % (protocol,host,port,web_root)

        if status == 0:

            params = {}
            params['apikey'] = apikey
            params['cmd'] = "forceProcess"

            params['dir'] = os.path.dirname(dirName)
            if remote_path:
                params['dir'] = joinPath(remote_path, os.path.basename(os.path.dirname(dirName)))

            release_status = self.get_status(url, apikey, dirName)

            if release_status:
                if release_status not in ["unprocessed", "snatched"]:
                    logger.warning("%s is marked with a status of %s, skipping ..." % (nzbName, release_status),section)
                    return 0
            else:
                logger.error("Could not find a status for %s" % (nzbName),section)
                return 1

            logger.debug("Opening URL: %s" % (url),section)

            try:
                r = requests.get(url, params=params)
            except requests.ConnectionError:
                logger.error("Unable to open URL %s" % (url),section)
                return 1  # failure

            logger.debug("Result: %s" % (r.text),section)
            if r.text == "OK":
                logger.postprocess("SUCCESS: Post-Processing started for %s in folder %s ..." % (nzbName, dirName),section)
            else:
                logger.error("FAILED: Post-Processing has NOT started for %s in folder %s. exiting!" % (nzbName, dirName),section)
                return 1 # failure

        else:
            logger.warning("FAILED DOWNLOAD DETECTED", section)
            return 0 # Success (as far as this script is concerned)

        # we will now wait 1 minutes for this album to be processed before returning to TorrentToMedia and unpausing.
        timeout = time.time() + 60 * wait_for
        while (time.time() < timeout):  # only wait 2 (default) minutes, then return.
            current_status = self.get_status(url, apikey, dirName)
            if current_status is not None and current_status != release_status:  # Something has changed. CPS must have processed this movie.
                logger.postprocess("SUCCESS: This release is now marked as status [%s]" % (current_status),section)
                return 0

            time.sleep(10 * wait_for)

        # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resule seeding now.
        logger.warning("The music album does not appear to have changed status after %s minutes. Please check your Logs" % (wait_for))
        return 1  # failure
