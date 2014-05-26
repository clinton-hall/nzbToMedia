import os
import time
import nzbtomedia
import requests
import time
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, replaceExtensions
from nzbtomedia import logger

class autoProcessComics:
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
            for issue in result:
                if os.path.basename(dirName) == issue['FolderName']:
                     return issue["Status"].lower()
        except:
            return None

    def processEpisode(self, section, dirName, inputName=None, status=0, clientAgent='manual', inputCategory=None):
        if status != 0:
            logger.warning("FAILED DOWNLOAD DETECTED, nothing to process.",section)
            return 0

        host = nzbtomedia.CFG[section][inputCategory]["host"]
        port = nzbtomedia.CFG[section][inputCategory]["port"]
        apikey = nzbtomedia.CFG[section][inputCategory]["apikey"]
        try:
            wait_for = int(nzbtomedia.CFG[section][inputCategory]["wait_for"])
        except:
            wait_for = 1
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

        inputName, dirName = convert_to_ascii(inputName, dirName)

        replaceExtensions(dirName)

        if remote_path:
            if remote_path[-1] in ['\\','/']:  # supplied directory includes final directory separator
                remote_path = remote_path + os.path.basename(dirName)
            elif remote_path[0] == '/':  # posix path
                remote_path = remote_path + '/' + os.path.basename(dirName)
            else:  # assume windows path or UNF path
                remote_path = remote_path + '\\' + os.path.basename(dirName)

        params = {}
        params['apikey'] = apikey
        params['cmd'] = "forceProcess"
        params['nzb_folder'] = dirName
        if remote_path:
            params['nzb_folder'] = remote_path

        if inputName != None:
            params['nzb_name'] = inputName

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        url = "%s%s:%s%s/api" % (protocol, host, port, web_root)

        release_status = self.get_status(url, apikey, dirName)
        if not release_status:
            logger.error("Could not find a status for %s, is it in the wanted list ?" % (inputName),section)
            return 1

        logger.debug("Opening URL: %s" % (url), section)

        try:
            r = requests.get(url, params=params, stream=True, verify=False)
        except requests.ConnectionError:
            logger.error("Unable to open URL", section)
            return 1 # failure

        for line in r.iter_lines():
            if line: logger.postprocess("%s" % (line), section)

        if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status %s" % (str(r.status_code)), section)
            return 1
        else:
            logger.postprocess("Post-Processing started for %s in folder %s ..." % (inputName, dirName),section)

        # we will now wait 1 minutes for this album to be processed before returning to TorrentToMedia and unpausing.
        timeout = time.time() + 60 * wait_for
        while (time.time() < timeout):  # only wait 1 (default) minutes, then return.
            current_status = self.get_status(url, apikey, dirName)
            if current_status is not None and current_status != release_status:  # Something has changed. Mylar must have processed this issue.
                logger.postprocess("SUCCESS: This issue is now marked as status [%s]" % (current_status),section)
                return 0

            time.sleep(10 * wait_for)

        # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resume seeding now.
        logger.warning("The issue does not appear to have changed status after %s minutes. Please check your Logs" % (wait_for),section)
        return 1  # failure
