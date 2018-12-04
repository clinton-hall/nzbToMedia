# coding=utf-8

import os
import core
import requests

from core.nzbToMediaUtil import convert_to_ascii, remoteDir, server_responding
from core import logger

requests.packages.urllib3.disable_warnings()


class autoProcessComics(object):
    def processEpisode(self, section, dirName, inputName=None, status=0, clientAgent='manual', inputCategory=None):

        apc_version = "2.04"
        comicrn_version = "1.01"

        cfg = dict(core.CFG[section][inputCategory])

        host = cfg["host"]
        port = cfg["port"]
        apikey = cfg["apikey"]
        ssl = int(cfg.get("ssl", 0))
        web_root = cfg.get("web_root", "")
        remote_path = int(cfg.get("remote_path"), 0)
        protocol = "https://" if ssl else "http://"

        url = "{0}{1}:{2}{3}/api".format(protocol, host, port, web_root)
        if not server_responding(url):
            logger.error("Server did not respond. Exiting", section)
            return [1, "{0}: Failed to post-process - {1} did not respond.".format(section, section)]

        inputName, dirName = convert_to_ascii(inputName, dirName)
        clean_name, ext = os.path.splitext(inputName)
        if len(ext) == 4:  # we assume this was a standard extension.
            inputName = clean_name

        params = {
            'cmd': 'forceProcess',
            'apikey': apikey,
            'nzb_folder': remoteDir(dirName) if remote_path else dirName,
        }

        if inputName is not None:
            params['nzb_name'] = inputName
        params['failed'] = int(status)
        params['apc_version'] = apc_version
        params['comicrn_version'] = comicrn_version

        success = False

        logger.debug("Opening URL: {0}".format(url), section)
        try:
            r = requests.post(url, params=params, stream=True, verify=False, timeout=(30, 300))
        except requests.ConnectionError:
            logger.error("Unable to open URL", section)
            return [1, "{0}: Failed to post-process - Unable to connect to {1}".format(section, section)]
        if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status {0}".format(r.status_code), section)
            return [1, "{0}: Failed to post-process - Server returned status {1}".format(section, r.status_code)]

        result = r.content
        if not type(result) == list:
            result = result.split('\n')
        for line in result:
            if line:
                logger.postprocess("{0}".format(line), section)
            if "Post Processing SUCCESSFUL" in line:
                success = True

        if success:
            logger.postprocess("SUCCESS: This issue has been processed successfully", section)
            return [0, "{0}: Successfully post-processed {1}".format(section, inputName)]
        else:
            logger.warning("The issue does not appear to have successfully processed. Please check your Logs", section)
            return [1, "{0}: Failed to post-process - Returned log from {1} was not as expected.".format(section, section)]
