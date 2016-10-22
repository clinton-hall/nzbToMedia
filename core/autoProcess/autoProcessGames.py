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

        cfg = dict(core.CFG[section][inputCategory])

        host = cfg["host"]
        port = cfg["port"]
        apikey = cfg["apikey"]
        library = cfg.get("library")
        ssl = int(cfg.get("ssl", 0))
        web_root = cfg.get("web_root", "")
        protocol = "https://" if ssl else "http://"

        url = "{0}{1}:{2}{3}/api".format(protocol, host, port, web_root)
        if not server_responding(url):
            logger.error("Server did not respond. Exiting", section)
            return [1, "{0}: Failed to post-process - {1} did not respond.".format(section, section)]

        inputName, dirName = convert_to_ascii(inputName, dirName)

        fields = inputName.split("-")

        gamezID = fields[0].replace("[", "").replace("]", "").replace(" ", "")

        downloadStatus = 'Downloaded' if status == 0 else 'Wanted'

        params = {
            'api_key': apikey,
            'mode': 'UPDATEREQUESTEDSTATUS',
            'db_id': gamezID,
            'status': downloadStatus
        }

        logger.debug("Opening URL: {0}".format(url), section)

        try:
            r = requests.get(url, params=params, verify=False, timeout=(30, 300))
        except requests.ConnectionError:
            logger.error("Unable to open URL")
            return [1, "{0}: Failed to post-process - Unable to connect to {1}".format(section, section)]

        result = r.json()
        logger.postprocess("{0}".format(result), section)
        if library:
            logger.postprocess("moving files to library: {0}".format(library), section)
            try:
                shutil.move(dirName, os.path.join(library, inputName))
            except:
                logger.error("Unable to move {0} to {1}".format(dirName, os.path.join(library, inputName)), section)
                return [1, "{0}: Failed to post-process - Unable to move files".format(section)]
        else:
            logger.error("No library specified to move files to. Please edit your configuration.", section)
            return [1, "{0}: Failed to post-process - No library defined in {1}".format(section, section)]

        if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status {0}".format(r.status_code), section)
            return [1, "{0}: Failed to post-process - Server returned status {1}".format(section, r.status_code)]
        elif result['success']:
            logger.postprocess("SUCCESS: Status for {0} has been set to {1} in Gamez".format(gamezID, downloadStatus), section)
            return [0, "{0}: Successfully post-processed {1}".format(section, inputName)]
        else:
            logger.error("FAILED: Status for {0} has NOT been updated in Gamez".format(gamezID), section)
            return [1, "{0}: Failed to post-process - Returned log from {1} was not as expected.".format(section, section)]
