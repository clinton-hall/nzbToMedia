# coding=utf-8

import os
import time
import requests
import core
import json

from core.nzbToMediaUtil import convert_to_ascii, rmDir, remoteDir, listMediaFiles, server_responding
from core.nzbToMediaSceneExceptions import process_all_exceptions
from core import logger

requests.packages.urllib3.disable_warnings()


class autoProcessMusic(object):
    def command_complete(self, url, params, headers, section):
        try:
            r = requests.get(url, params=params, headers=headers, stream=True, verify=False, timeout=(30, 60))
        except requests.ConnectionError:
            logger.error("Unable to open URL: {0}".format(url), section)
            return None
        if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status {0}".format(r.status_code), section)
            return None
        else:
            try:
                return r.json()['state']
            except (ValueError, KeyError):
                # ValueError catches simplejson's JSONDecodeError and json's ValueError
                logger.error("{0} did not return expected json data.".format(section), section)
                return None

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

    def forceProcess(self, params, url, apikey, inputName, dirName, section, wait_for):
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
        delete_failed = int(cfg["delete_failed"])
        web_root = cfg.get("web_root", "")
        remote_path = int(cfg.get("remote_path", 0))
        protocol = "https://" if ssl else "http://"
        status = int(status)
        if status > 0 and core.NOEXTRACTFAILED:
            extract = 0
        else:
            extract = int(cfg.get("extract", 0))

        if section == "Lidarr":
            url = "{0}{1}:{2}{3}/api/v1".format(protocol, host, port, web_root)
        else:
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

        #if listMediaFiles(dirName, media=False, audio=True, meta=False, archives=False) and status:
        #    logger.info("Status shown as failed from Downloader, but valid video files found. Setting as successful.", section)
        #    status = 0

        if status == 0 and section == "HeadPhones":

            params = {
                'apikey': apikey,
                'cmd': "forceProcess",
                'dir': remoteDir(dirName) if remote_path else dirName
            }

            res = self.forceProcess(params, url, apikey, inputName, dirName, section, wait_for)
            if res[0] in [0, 1]:
                return res

            params = {
                'apikey': apikey,
                'cmd': "forceProcess",
                'dir': os.path.split(remoteDir(dirName))[0] if remote_path else os.path.split(dirName)[0]
            }

            res = self.forceProcess(params, url, apikey, inputName, dirName, section, wait_for)
            if res[0] in [0, 1]:
                return res

            # The status hasn't changed. uTorrent can resume seeding now.
            logger.warning("The music album does not appear to have changed status after {0} minutes. Please check your Logs".format(wait_for), section)
            return [1, "{0}: Failed to post-process - No change in wanted status".format(section)]

        elif status == 0 and section == "Lidarr":
            url = "{0}{1}:{2}{3}/api/v1/command".format(protocol, host, port, web_root)
            headers = {"X-Api-Key": apikey}
            if remote_path:
                logger.debug("remote_path: {0}".format(remoteDir(dirName)), section)
                data = {"name": "Rename", "path": remoteDir(dirName)}
            else:
                logger.debug("path: {0}".format(dirName), section)
                data = {"name": "Rename", "path": dirName}
            data = json.dumps(data)
            try:
                logger.debug("Opening URL: {0} with data: {1}".format(url, data), section)
                r = requests.post(url, data=data, headers=headers, stream=True, verify=False, timeout=(30, 1800))
            except requests.ConnectionError:
                logger.error("Unable to open URL: {0}".format(url), section)
                return [1, "{0}: Failed to post-process - Unable to connect to {1}".format(section, section)]

            Success = False
            Queued = False
            Started = False
            try:
                res = json.loads(r.content)
                scan_id = int(res['id'])
                logger.debug("Scan started with id: {0}".format(scan_id), section)
                Started = True
            except Exception as e:
                logger.warning("No scan id was returned due to: {0}".format(e), section)
                scan_id = None
                Started = False
                return [1, "{0}: Failed to post-process - Unable to start scan".format(section)]

            n = 0
            params = {}
            url = "{0}/{1}".format(url, scan_id)
            while n < 6:  # set up wait_for minutes to see if command completes..
                time.sleep(10 * wait_for)
                command_status = self.command_complete(url, params, headers, section)
                if command_status and command_status in ['completed', 'failed']:
                    break
                n += 1
            if command_status:
                logger.debug("The Scan command return status: {0}".format(command_status), section)
            if not os.path.exists(dirName):
                logger.debug("The directory {0} has been removed. Renaming was successful.".format(dirName), section)
                return [0, "{0}: Successfully post-processed {1}".format(section, inputName)]
            elif command_status and command_status in ['completed']:
                logger.debug("The Scan command has completed successfully. Renaming was successful.", section)
                return [0, "{0}: Successfully post-processed {1}".format(section, inputName)]
            elif command_status and command_status in ['failed']:
                logger.debug("The Scan command has failed. Renaming was not successful.", section)
                # return [1, "%s: Failed to post-process %s" % (section, inputName) ]
            else:
                logger.debug("The Scan command did not return status completed. Passing back to {0} to attempt complete download handling.".format(section), section)
                return [status, "{0}: Passing back to {1} to attempt Complete Download Handling".format(section, section)]

        else:
            if section == "Lidarr":
                logger.postprocess("FAILED: The download failed. Sending failed download to {0} for CDH processing".format(section), section)
                return [1, "{0}: Download Failed. Sending back to {1}".format(section, section)]  # Return as failed to flag this in the downloader.
            else:
                logger.warning("FAILED DOWNLOAD DETECTED", section)
                if delete_failed and os.path.isdir(dirName) and not os.path.dirname(dirName) == dirName:
                    logger.postprocess("Deleting failed files and folder {0}".format(dirName), section)
                    rmDir(dirName)
                return [1, "{0}: Failed to post-process. {1} does not support failed downloads".format(section, section)]  # Return as failed to flag this in the downloader.