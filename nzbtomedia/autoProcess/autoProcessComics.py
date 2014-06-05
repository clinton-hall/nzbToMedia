import os
import time
import nzbtomedia
import requests
import time
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, replaceExtensions, remoteDir
from nzbtomedia import logger

class autoProcessComics:
    def processEpisode(self, section, dirName, inputName=None, status=0, clientAgent='manual', inputCategory=None):
        if status != 0:
            logger.warning("FAILED DOWNLOAD DETECTED, nothing to process.",section)
            return 0

        host = nzbtomedia.CFG[section][inputCategory]["host"]
        port = nzbtomedia.CFG[section][inputCategory]["port"]
        username = nzbtomedia.CFG[section][inputCategory]["username"]
        password = nzbtomedia.CFG[section][inputCategory]["password"]
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

        inputName, dirName = convert_to_ascii(inputName, dirName)

        replaceExtensions(dirName)

        clean_name, ext = os.path.splitext(inputName)
        if len(ext) == 4:  # we assume this was a standrard extension. 
            inputName = clean_name

        params = {}
        params['nzb_folder'] = dirName
        if remote_path:
            params['nzb_folder'] = remoteDir(dirName)

        if inputName != None:
            params['nzb_name'] = inputName

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        url = "%s%s:%s%s/post_process" % (protocol, host, port, web_root)

        success = False

        logger.debug("Opening URL: %s" % (url), section)

        try:
            r = requests.get(url, auth=(username, password), params=params, stream=True, verify=False)
        except requests.ConnectionError:
            logger.error("Unable to open URL", section)
            return 1 # failure

        for line in r.iter_lines():
            if line: logger.postprocess("%s" % (line), section)
            if "Post Processing SUCCESSFUL!" in line: success = True

        if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status %s" % (str(r.status_code)), section)
            return 1

        if success:
            logger.postprocess("SUCCESS: This issue has been processed successfully",section)
            return 0
        else:
            logger.warning("The issue does not appear to have successfully processed. Please check your Logs",section)
            return 1  # failure