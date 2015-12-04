import os
import time
import core
import requests
import time

from core.nzbToMediaUtil import convert_to_ascii, remoteDir, server_responding
from core.nzbToMediaSceneExceptions import process_all_exceptions
from core import logger

requests.packages.urllib3.disable_warnings()

class autoProcessComics:
    def processEpisode(self, section, dirName, inputName=None, status=0, clientAgent='manual', inputCategory=None):
        if int(status) != 0:
            logger.warning("FAILED DOWNLOAD DETECTED, nothing to process.",section)
            return [1, "%s: Failed to post-process. %s does not support failed downloads" % (section, section) ]

        host = core.CFG[section][inputCategory]["host"]
        port = core.CFG[section][inputCategory]["port"]
        username = core.CFG[section][inputCategory]["username"]
        password = core.CFG[section][inputCategory]["password"]
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

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        url = "%s%s:%s%s/post_process" % (protocol, host, port, web_root)
        if not server_responding(url):
            logger.error("Server did not respond. Exiting", section)
            return [1, "%s: Failed to post-process - %s did not respond." % (section, section) ]

        inputName, dirName = convert_to_ascii(inputName, dirName)
        clean_name, ext = os.path.splitext(inputName)
        if len(ext) == 4:  # we assume this was a standrard extension. 
            inputName = clean_name

        params = {}
        params['nzb_folder'] = dirName

        if remote_path:
            params['nzb_folder'] = remoteDir(dirName)

        if inputName != None:
            params['nzb_name'] = inputName

        success = False

        logger.debug("Opening URL: %s" % (url), section)
        try:
            r = requests.get(url, auth=(username, password), params=params, stream=True, verify=False, timeout=(30, 300))
        except requests.ConnectionError:
            logger.error("Unable to open URL", section)
            return [1, "%s: Failed to post-process - Unable to connect to %s" % (section, section) ]
        for line in r.iter_lines():
            if line: logger.postprocess("%s" % (line), section)
            if ("Post Processing SUCCESSFUL!" or "Post Processing SUCCESSFULL!")in line: success = True

        if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status %s" % (str(r.status_code)), section)
            return [1, "%s: Failed to post-process - Server returned status %s" % (section, str(r.status_code)) ]

        if success:
            logger.postprocess("SUCCESS: This issue has been processed successfully",section)
            return [0, "%s: Successfully post-processed %s" % (section, inputName) ]
        else:
            logger.warning("The issue does not appear to have successfully processed. Please check your Logs",section)
            return [1, "%s: Failed to post-process - Returned log from %s was not as expected." % (section, section) ]
