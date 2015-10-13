import os
import time
import requests
import core

from core.nzbToMediaUtil import convert_to_ascii, remoteDir, listMediaFiles, server_responding
from core.nzbToMediaSceneExceptions import process_all_exceptions
from core import logger

requests.packages.urllib3.disable_warnings()

class autoProcessMusic:
    def get_status(self, url, apikey, dirName):
        logger.debug("Attempting to get current status for release:%s" % (os.path.basename(dirName)))

        params = {}
        params['apikey'] = apikey
        params['cmd'] = "getHistory"

        logger.debug("Opening URL: %s with PARAMS: %s" % (url, params))

        try:
            r = requests.get(url, params=params, verify=False, timeout=(30, 120))
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

        host = core.CFG[section][inputCategory]["host"]
        port = core.CFG[section][inputCategory]["port"]
        apikey = core.CFG[section][inputCategory]["apikey"]
        wait_for = int(core.CFG[section][inputCategory]["wait_for"])

        try:
            ssl = int(core.CFG[section][inputCategory]["ssl"])
        except:
            ssl = 0
        try:
            web_root = core.CFG[section][inputCategory]["web_root"]
        except:
            web_root = ""
        try:
            remote_path = int(core.CFG[section][inputCategory]["remote_path"])
        except:
            remote_path = 0
        try:
            extract = int(section[inputCategory]["extract"])
        except:
            extract = 0

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"


        url = "%s%s:%s%s/api" % (protocol,host,port,web_root)
        if not server_responding(url):
            logger.error("Server did not respond. Exiting", section)
            return [1, "%s: Failed to post-process - %s did not respond." % (section, section) ]

        if not os.path.isdir(dirName) and os.path.isfile(dirName): # If the input directory is a file, assume single file download and split dir/name.
            dirName = os.path.split(os.path.normpath(dirName))[0]

        SpecificPath = os.path.join(dirName, str(inputName))
        cleanName = os.path.splitext(SpecificPath)
        if cleanName[1] == ".nzb":
            SpecificPath = cleanName[0]
        if os.path.isdir(SpecificPath):
            dirName = SpecificPath

        process_all_exceptions(inputName, dirName)
        inputName, dirName = convert_to_ascii(inputName, dirName)

        if not listMediaFiles(dirName, media=False, audio=True, meta=False, archives=False) and listMediaFiles(dirName, media=False, audio=False, meta=False, archives=True) and extract:
            logger.debug('Checking for archives to extract in directory: %s' % (dirName))
            core.extractFiles(dirName)
            inputName, dirName = convert_to_ascii(inputName, dirName)

        if listMediaFiles(dirName, media=False, audio=True, meta=False, archives=False) and status:
            logger.info("Status shown as failed from Downloader, but %s valid video files found. Setting as successful." % (str(good_files)), section)
            status = 0

        if status == 0:

            params = {}
            params['apikey'] = apikey
            params['cmd'] = "forceProcess"

            params['dir'] = os.path.dirname(dirName)
            if remote_path:
                params['dir'] = remoteDir(os.path.dirname(dirName))

            release_status = self.get_status(url, apikey, dirName)
            if not release_status:
                logger.error("Could not find a status for %s, is it in the wanted list ?" % (inputName),section)

            logger.debug("Opening URL: %s with PARAMS: %s" % (url, params), section)

            try:
                r = requests.get(url, params=params, verify=False, timeout=(30, 300))
            except requests.ConnectionError:
                logger.error("Unable to open URL %s" % (url) ,section)
                return [1, "%s: Failed to post-process - Unable to connect to %s" % (section, section) ]

            logger.debug("Result: %s" % (r.text),section)

            if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
                logger.error("Server returned status %s" % (str(r.status_code)), section)
                return [1, "%s: Failed to post-process - Server returned status %s" % (section, str(r.status_code)) ]
            elif r.text == "OK":
                logger.postprocess("SUCCESS: Post-Processing started for %s in folder %s ..." % (inputName, dirName),section) 
            else:
                logger.error("FAILED: Post-Processing has NOT started for %s in folder %s. exiting!" % (inputName, dirName),section)
                return [1, "%s: Failed to post-process - Returned log from %s was not as expected." % (section, section) ]

        else:
            logger.warning("FAILED DOWNLOAD DETECTED", section)
            return [1, "%s: Failed to post-process. %s does not support failed downloads" % (section, section) ]

        # we will now wait for this album to be processed before returning to TorrentToMedia and unpausing.
        timeout = time.time() + 60 * wait_for
        while (time.time() < timeout):
            current_status = self.get_status(url, apikey, dirName)
            if current_status is not None and current_status != release_status:  # Something has changed. CPS must have processed this movie.
                logger.postprocess("SUCCESS: This release is now marked as status [%s]" % (current_status),section)
                return [0, "%s: Successfully post-processed %s" % (section, inputName) ]
            if not os.path.isdir(dirName):
                logger.postprocess("SUCCESS: The input directory %s has been removed Processing must have finished." % (dirName),section)
                return [0, "%s: Successfully post-processed %s" % (section, inputName) ]
            time.sleep(10 * wait_for)

        # The status hasn't changed. uTorrent can resume seeding now.
        logger.warning("The music album does not appear to have changed status after %s minutes. Please check your Logs" % (wait_for),section)
        return [1, "%s: Failed to post-process - No change in wanted status" % (section) ]
