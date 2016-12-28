# coding=utf-8

import os
import time
import requests
import core

from core.nzbToMediaUtil import convert_to_ascii, remoteDir, listMediaFiles, server_responding
from core.nzbToMediaSceneExceptions import process_all_exceptions
from core import logger

requests.packages.urllib3.disable_warnings()


class autoProcessMusic(object):
    def get_status(self, url, apikey, dirName):
        logger.debug("Attempting to get current status for release:{0}".format(os.path.basename(dirName)))

        params = {
            'apikey': apikey,
            'cmd': "getHistory"
        }

        logger.debug("Opening URL: {0} with PARAMS: {1}".format(url, params))

        try:
            r = requests.get(url, params=params, verify=False, timeout=(30, 120))
        except requests.RequestException:
            logger.error("Unable to open URL")
            return None

        try:
            result = r.json()
        except ValueError:
            # ValueError catches simplejson's JSONDecodeError and json's ValueError
            return None

        for album in result:
            if os.path.basename(dirName) == album['FolderName']:
                return album["Status"].lower()

    def forceProcess(params):
        release_status = self.get_status(url, apikey, dirName)
        if not release_status:
            logger.error("Could not find a status for {0}, is it in the wanted list ?".format(inputName), section)

        logger.debug("Opening URL: {0} with PARAMS: {1}".format(url, params), section)

        try:
            r = requests.get(url, params=params, verify=False, timeout=(30, 300))
        except requests.ConnectionError:
            logger.error("Unable to open URL {0}".format(url), section)
            return [1, "{0}: Failed to post-process - Unable to connect to {1}".format(section, section)]

        logger.debug("Result: {0}".format(r.text), section)

        if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status {0}".format(r.status_code), section)
            return [1, "{0}: Failed to post-process - Server returned status {1}".format(section, r.status_code)]
        elif r.text == "OK":
            logger.postprocess("SUCCESS: Post-Processing started for {0} in folder {1} ...".format(inputName, dirName), section)
        else:
            logger.error("FAILED: Post-Processing has NOT started for {0} in folder {1}. exiting!".format(inputName, dirName), section)
            return [1, "{0}: Failed to post-process - Returned log from {1} was not as expected.".format(section, section)]

        # we will now wait for this album to be processed before returning to TorrentToMedia and unpausing.
        timeout = time.time() + 60 * wait_for
        while time.time() < timeout:
            current_status = self.get_status(url, apikey, dirName)
            if current_status is not None and current_status != release_status:  # Something has changed. CPS must have processed this movie.
                logger.postprocess("SUCCESS: This release is now marked as status [{0}]".format(current_status), section)
                return [0, "{0}: Successfully post-processed {1}".format(section, inputName)]
            if not os.path.isdir(dirName):
                logger.postprocess("SUCCESS: The input directory {0} has been removed Processing must have finished.".format(dirName), section)
                return [0, "{0}: Successfully post-processed {1}".format(section, inputName)]
            time.sleep(10 * wait_for)
        # The status hasn't changed.
        return [2, "no change"]

    def process(self, section, dirName, inputName=None, status=0, clientAgent="manual", inputCategory=None):
        status = int(status)

        cfg = dict(core.CFG[section][inputCategory])

        host = cfg["host"]
        port = cfg["port"]
        apikey = cfg["apikey"]
        wait_for = int(cfg["wait_for"])
        ssl = int(cfg.get("ssl", 0))
        web_root = cfg.get("web_root", "")
        remote_path = int(cfg.get("remote_path", 0))
        protocol = "https://" if ssl else "http://"
        status = int(status)
        if status > 0 and core.NOEXTRACTFAILED:
            extract = 0
        else:
            extract = int(cfg.get("extract", 0))

        url = "{0}{1}:{2}{3}/api".format(protocol, host, port, web_root)
        if not server_responding(url):
            logger.error("Server did not respond. Exiting", section)
            return [1, "{0}: Failed to post-process - {1} did not respond.".format(section, section)]

        if not os.path.isdir(dirName) and os.path.isfile(dirName):  # If the input directory is a file, assume single file download and split dir/name.
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
            logger.debug('Checking for archives to extract in directory: {0}'.format(dirName))
            core.extractFiles(dirName)
            inputName, dirName = convert_to_ascii(inputName, dirName)

        if listMediaFiles(dirName, media=False, audio=True, meta=False, archives=False) and status:
            logger.info("Status shown as failed from Downloader, but valid video files found. Setting as successful.", section)
            status = 0

        if status == 0:

            params = {
                'apikey': apikey,
                'cmd': "forceProcess",
                'dir': remoteDir(dirName) if remote_path else dirName
            }

            res = forceProcess(params)
            if res[0] in [0, 1]:
                return res

            params = {
                'apikey': apikey,
                'cmd': "forceProcess",
                'dir': os.path.split(remoteDir(dirName))[0] if remote_path else os.path.split(dirName)[0]
            }

            res = forceProcess(params)
            if res[0] in [0, 1]:
                return res

            # The status hasn't changed. uTorrent can resume seeding now.
            logger.warning("The music album does not appear to have changed status after {0} minutes. Please check your Logs".format(wait_for), section)
            return [1, "{0}: Failed to post-process - No change in wanted status".format(section)]

        else:
            logger.warning("FAILED DOWNLOAD DETECTED", section)
            return [1, "{0}: Failed to post-process. {1} does not support failed downloads".format(section, section)]