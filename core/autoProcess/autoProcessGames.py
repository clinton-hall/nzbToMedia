# coding=utf-8

import os
import core
import requests
import shutil

from core.nzbToMediaUtil import convert_to_ascii, server_responding
from core import logger

requests.packages.urllib3.disable_warnings()


class autoProcessGames(object):
    def process(self, section, dirName, inputName=None, status=0, clientAgent='manual', inputCategory=None):
        status = int(status)

        host = core.CFG[section][inputCategory]["host"]
        port = core.CFG[section][inputCategory]["port"]
        apikey = core.CFG[section][inputCategory]["apikey"]
        library = core.CFG[section][inputCategory].get("library")
        ssl = int(core.CFG[section][inputCategory].get("ssl", 0))
        web_root = core.CFG[section][inputCategory].get("web_root", "")

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        url = "%s%s:%s%s/api" % (protocol, host, port, web_root)
        if not server_responding(url):
            logger.error("Server did not respond. Exiting", section)
            return [1, "%s: Failed to post-process - %s did not respond." % (section, section)]

        inputName, dirName = convert_to_ascii(inputName, dirName)

        fields = inputName.split("-")

        gamezID = fields[0].replace("[", "").replace("]", "").replace(" ", "")

        downloadStatus = 'Wanted'
        if status == 0:
            downloadStatus = 'Downloaded'

        params = {
            'api_key': apikey,
            'mode': 'UPDATEREQUESTEDSTATUS',
            'db_id': gamezID,
            'status': downloadStatus
        }

        logger.debug("Opening URL: %s" % (url), section)

        try:
            r = requests.get(url, params=params, verify=False, timeout=(30, 300))
        except requests.ConnectionError:
            logger.error("Unable to open URL")
            return [1, "%s: Failed to post-process - Unable to connect to %s" % (section, section)]

        result = r.json()
        logger.postprocess("%s" % (result), section)
        if library:
            logger.postprocess("moving files to library: %s" % (library), section)
            try:
                shutil.move(dirName, os.path.join(library, inputName))
            except:
                logger.error("Unable to move %s to %s" % (dirName, os.path.join(library, inputName)), section)
                return [1, "%s: Failed to post-process - Unable to move files" % (section)]
        else:
            logger.error("No library specified to move files to. Please edit your configuration.", section)
            return [1, "%s: Failed to post-process - No library defined in %s" % (section, section)]

        if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status %s" % (str(r.status_code)), section)
            return [1, "%s: Failed to post-process - Server returned status %s" % (section, str(r.status_code))]
        elif result['success']:
            logger.postprocess("SUCCESS: Status for %s has been set to %s in Gamez" % (gamezID, downloadStatus), section)
            return [0, "%s: Successfully post-processed %s" % (section, inputName)]
        else:
            logger.error("FAILED: Status for %s has NOT been updated in Gamez" % (gamezID), section)
            return [1, "%s: Failed to post-process - Returned log from %s was not as expected." % (section, section)]
