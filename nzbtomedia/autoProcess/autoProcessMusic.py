import os
import time
import requests
import nzbtomedia

from nzbtomedia.nzbToMediaUtil import convert_to_ascii, remoteDir, listMediaFiles
from nzbtomedia.nzbToMediaSceneExceptions import process_all_exceptions
from nzbtomedia import logger

class autoProcessMusic:
    def get_status(self, url, apikey, dirName):
        logger.debug("Attempting to get current status for release:%s" % (os.path.basename(dirName)))

        params = {}
        params['apikey'] = apikey
        params['cmd'] = "getHistory"

        logger.debug("Opening URL: %s with PARAMS: %s" % (url, params))

        try:
            r = requests.get(url, params=params, verify=False)
        except Exception, e:
            logger.error("Unable to open URL")
            return None

        try:
            result = r.json()
            for album in result:
                if os.path.basename(dirName) == album['FolderName']:
                     return album["Status"].lower()
        except:
            return None

    def process(self, section, dirName, inputName=None, status=0, clientAgent="manual", inputCategory=None):
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
            remote_path = int(nzbtomedia.CFG[section][inputCategory]["remote_path"])
        except:
            remote_path = 0

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

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

        if not listMediaFiles(dirName, media=False, audio=True, meta=False, archives=False) and listMediaFiles(dirName, media=False, audio=False, meta=False, archives=True):
            logger.debug('Checking for archives to extract in directory: %s' % (dirName))
            nzbtomedia.extractFiles(dirName)
            inputName, dirName = convert_to_ascii(inputName, dirName)

        if listMediaFiles(dirName, media=False, audio=True, meta=False, archives=False) and status:
            logger.info("Status shown as failed from Downloader, but %s valid video files found. Setting as successful." % (str(good_files)), section)
            status = 0

        url = "%s%s:%s%s/api" % (protocol,host,port,web_root)

        if status == 0:

            params = {}
            params['apikey'] = apikey
            params['cmd'] = "forceProcess"

            params['dir'] = os.path.dirname(dirName)
            if remote_path:
                params['dir'] = remoteDir(dirName)

            release_status = self.get_status(url, apikey, dirName)
            if not release_status:
                logger.error("Could not find a status for %s, is it in the wanted list ?" % (inputName),section)

            logger.debug("Opening URL: %s with PARAMS: %s" % (url, params), section)

            try:
                r = requests.get(url, params=params, verify=False)
            except requests.ConnectionError:
                logger.error("Unable to open URL %s" % (url) ,section)
                return 1  # failure

            logger.debug("Result: %s" % (r.text),section)

            if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                logger.error("Server returned status %s" % (str(r.status_code)), section)
                return 1
            elif r.text == "OK":
                logger.postprocess("SUCCESS: Post-Processing started for %s in folder %s ..." % (inputName, dirName),section) 
            else:
                logger.error("FAILED: Post-Processing has NOT started for %s in folder %s. exiting!" % (inputName, dirName),section)
                return 1 # failure

        else:
            logger.warning("FAILED DOWNLOAD DETECTED", section)
            return 0 # Success (as far as this script is concerned)

        # we will now wait for this album to be processed before returning to TorrentToMedia and unpausing.
        timeout = time.time() + 60 * wait_for
        while (time.time() < timeout):
            current_status = self.get_status(url, apikey, dirName)
            if current_status is not None and current_status != release_status:  # Something has changed. CPS must have processed this movie.
                logger.postprocess("SUCCESS: This release is now marked as status [%s]" % (current_status),section)
                return 0
            if not os.path.isdir(dirName):
                logger.postprocess("SUCCESS: The input directory %s has been removed Processing must have finished." % (dirName),section)
                return 0
            time.sleep(10 * wait_for)

        # The status hasn't changed. uTorrent can resume seeding now.
        logger.warning("The music album does not appear to have changed status after %s minutes. Please check your Logs" % (wait_for),section)
        return 1  # failure
