# coding=utf-8

import copy
import os
import time
import errno
import requests
import json
import core

from core.nzbToMediaAutoFork import autoFork
from core.nzbToMediaSceneExceptions import process_all_exceptions
from core.nzbToMediaUtil import convert_to_ascii, flatten, rmDir, listMediaFiles, remoteDir, import_subs, server_responding, reportNzb
from core import logger
from core.transcoder import transcoder

requests.packages.urllib3.disable_warnings()


class autoProcessTV(object):
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

    def CDH(self, url2, headers, section="MAIN"):
        try:
            r = requests.get(url2, params={}, headers=headers, stream=True, verify=False, timeout=(30, 60))
        except requests.ConnectionError:
            logger.error("Unable to open URL: {0}".format(url2), section)
            return False
        if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status {0}".format(r.status_code), section)
            return False
        else:
            try:
                return r.json().get("enableCompletedDownloadHandling", False)
            except ValueError:
                # ValueError catches simplejson's JSONDecodeError and json's ValueError
                return False

    def processEpisode(self, section, dirName, inputName=None, failed=False, clientAgent="manual", download_id=None, inputCategory=None, failureLink=None):

        cfg = dict(core.CFG[section][inputCategory])

        host = cfg["host"]
        port = cfg["port"]
        ssl = int(cfg.get("ssl", 0))
        web_root = cfg.get("web_root", "")
        protocol = "https://" if ssl else "http://"
        username = cfg.get("username", "")
        password = cfg.get("password", "")
        apikey = cfg.get("apikey", "")

        if server_responding("{0}{1}:{2}{3}".format(protocol, host, port, web_root)):
            # auto-detect correct fork
            fork, fork_params = autoFork(section, inputCategory)
        elif not username and not apikey:
            logger.info('No SickBeard username or Sonarr apikey entered. Performing transcoder functions only')
            fork, fork_params = "None", {}
        else:
            logger.error("Server did not respond. Exiting", section)
            return [1, "{0}: Failed to post-process - {1} did not respond.".format(section, section)]

        delete_failed = int(cfg.get("delete_failed", 0))
        nzbExtractionBy = cfg.get("nzbExtractionBy", "Downloader")
        process_method = cfg.get("process_method")
        if  clientAgent == core.TORRENT_CLIENTAGENT and core.USELINK == "move-sym":
            process_method = "symlink"
        remote_path = int(cfg.get("remote_path", 0))
        wait_for = int(cfg.get("wait_for", 2))
        force = int(cfg.get("force", 0))
        delete_on = int(cfg.get("delete_on", 0))
        ignore_subs = int(cfg.get("ignore_subs", 0))
        status = int(failed)
        if status > 0 and core.NOEXTRACTFAILED:
            extract = 0
        else:
            extract = int(cfg.get("extract", 0))
        #get importmode, default to "Move" for consistency with legacy
        importMode = cfg.get("importMode","Move")

        if not os.path.isdir(dirName) and os.path.isfile(dirName):  # If the input directory is a file, assume single file download and split dir/name.
            dirName = os.path.split(os.path.normpath(dirName))[0]

        SpecificPath = os.path.join(dirName, str(inputName))
        cleanName = os.path.splitext(SpecificPath)
        if cleanName[1] == ".nzb":
            SpecificPath = cleanName[0]
        if os.path.isdir(SpecificPath):
            dirName = SpecificPath

        # Attempt to create the directory if it doesn't exist and ignore any
        # error stating that it already exists. This fixes a bug where SickRage
        # won't process the directory because it doesn't exist.
        try:
            os.makedirs(dirName)  # Attempt to create the directory
        except OSError as e:
            # Re-raise the error if it wasn't about the directory not existing
            if e.errno != errno.EEXIST:
                raise

        if 'process_method' not in fork_params or (clientAgent in ['nzbget', 'sabnzbd'] and nzbExtractionBy != "Destination"):
            if inputName:
                process_all_exceptions(inputName, dirName)
                inputName, dirName = convert_to_ascii(inputName, dirName)

            # Now check if tv files exist in destination. 
            if not listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False):
                if listMediaFiles(dirName, media=False, audio=False, meta=False, archives=True) and extract:
                    logger.debug('Checking for archives to extract in directory: {0}'.format(dirName))
                    core.extractFiles(dirName)
                    inputName, dirName = convert_to_ascii(inputName, dirName)

            if listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False):  # Check that a video exists. if not, assume failed.
                flatten(dirName)

        # Check video files for corruption
        good_files = 0
        num_files = 0
        for video in listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False):
            num_files += 1
            if transcoder.isVideoGood(video, status):
                good_files += 1
                import_subs(video)
        if num_files > 0:
            if good_files == num_files and not status == 0:
                logger.info('Found Valid Videos. Setting status Success')
                status = 0
                failed = 0
            if good_files < num_files and status == 0:
                logger.info('Found corrupt videos. Setting status Failed')
                status = 1
                failed = 1
                if 'NZBOP_VERSION' in os.environ and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
                    print('[NZB] MARK=BAD')
                if failureLink:
                    failureLink += '&corrupt=true'
        elif clientAgent == "manual":
            logger.warning("No media files found in directory {0} to manually process.".format(dirName), section)
            return [0, ""]  # Success (as far as this script is concerned)
        elif nzbExtractionBy == "Destination":
            logger.info("Check for media files ignored because nzbExtractionBy is set to Destination.")
            if int(failed) == 0:
                logger.info("Setting Status Success.")
                status = 0
                failed = 0
            else:
                logger.info("Downloader reported an error during download or verification. Processing this as a failed download.")
                status = 1
                failed = 1
        else:
            logger.warning("No media files found in directory {0}. Processing this as a failed download".format(dirName), section)
            status = 1
            failed = 1
            if 'NZBOP_VERSION' in os.environ and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
                print('[NZB] MARK=BAD')

        if status == 0 and core.TRANSCODE == 1:  # only transcode successful downloads
            result, newDirName = transcoder.Transcode_directory(dirName)
            if result == 0:
                logger.debug("SUCCESS: Transcoding succeeded for files in {0}".format(dirName), section)
                dirName = newDirName

                chmod_directory = int(str(cfg.get("chmodDirectory", "0")), 8)
                logger.debug("Config setting 'chmodDirectory' currently set to {0}".format(oct(chmod_directory)), section)
                if chmod_directory:
                    logger.info("Attempting to set the octal permission of '{0}' on directory '{1}'".format(oct(chmod_directory), dirName), section)
                    core.rchmod(dirName, chmod_directory)
            else:
                logger.error("FAILED: Transcoding failed for files in {0}".format(dirName), section)
                return [1, "{0}: Failed to post-process - Transcoding failed".format(section)]

        # configure SB params to pass
        fork_params['quiet'] = 1
        fork_params['proc_type'] = 'manual'
        if inputName is not None:
            fork_params['nzbName'] = inputName

        for param in copy.copy(fork_params):
            if param == "failed":
                fork_params[param] = failed
                del fork_params['proc_type']
                if "type" in fork_params:
                    del fork_params['type']

            if param == "return_data":
                fork_params[param] = 0
                del fork_params['quiet']

            if param == "type":
                fork_params[param] = 'manual'
                if "proc_type" in fork_params:
                    del fork_params['proc_type']

            if param in ["dirName", "dir", "proc_dir", "process_directory", "path"]:
                fork_params[param] = dirName
                if remote_path:
                    fork_params[param] = remoteDir(dirName)

            if param == "process_method":
                if process_method:
                    fork_params[param] = process_method
                else:
                    del fork_params[param]

            if param in ["force", "force_replace"]:
                if force:
                    fork_params[param] = force
                else:
                    del fork_params[param]

            if param in ["delete_on", "delete"]:
                if delete_on:
                    fork_params[param] = delete_on
                else:
                    del fork_params[param]

            if param == "ignore_subs":
                if ignore_subs:
                    fork_params[param] = ignore_subs
                else:
                    del fork_params[param]

            if param == "force_next":
                fork_params[param] = 1

        # delete any unused params so we don't pass them to SB by mistake
        [fork_params.pop(k) for k, v in fork_params.items() if v is None]

        if status == 0:
            if section == "NzbDrone" and not apikey:
                logger.info('No Sonarr apikey entered. Processing completed.')
                return [0, "{0}: Successfully post-processed {1}".format(section, inputName)]
            logger.postprocess("SUCCESS: The download succeeded, sending a post-process request", section)
        else:
            core.FAILED = True
            if failureLink:
                reportNzb(failureLink, clientAgent)
            if 'failed' in fork_params:
                logger.postprocess("FAILED: The download failed. Sending 'failed' process request to {0} branch".format(fork), section)
            elif section == "NzbDrone":
                logger.postprocess("FAILED: The download failed. Sending failed download to {0} for CDH processing".format(fork), section)
                return [1, "{0}: Download Failed. Sending back to {1}".format(section, section)]  # Return as failed to flag this in the downloader.
            else:
                logger.postprocess("FAILED: The download failed. {0} branch does not handle failed downloads. Nothing to process".format(fork), section)
                if delete_failed and os.path.isdir(dirName) and not os.path.dirname(dirName) == dirName:
                    logger.postprocess("Deleting failed files and folder {0}".format(dirName), section)
                    rmDir(dirName)
                return [1, "{0}: Failed to post-process. {1} does not support failed downloads".format(section, section)]  # Return as failed to flag this in the downloader.

        url = None
        if section == "SickBeard":
            if apikey:
                url = "{0}{1}:{2}{3}/api/{4}/?cmd=postprocess".format(protocol, host, port, web_root, apikey)
            else:
                url = "{0}{1}:{2}{3}/home/postprocess/processEpisode".format(protocol, host, port, web_root)
        elif section == "NzbDrone":
            url = "{0}{1}:{2}{3}/api/command".format(protocol, host, port, web_root)
            url2 = "{0}{1}:{2}{3}/api/config/downloadClient".format(protocol, host, port, web_root)
            headers = {"X-Api-Key": apikey}
            # params = {'sortKey': 'series.title', 'page': 1, 'pageSize': 1, 'sortDir': 'asc'}
            if remote_path:
                logger.debug("remote_path: {0}".format(remoteDir(dirName)), section)
                data = {"name": "DownloadedEpisodesScan", "path": remoteDir(dirName), "downloadClientId": download_id, "importMode": importMode}
            else:
                logger.debug("path: {0}".format(dirName), section)
                data = {"name": "DownloadedEpisodesScan", "path": dirName, "downloadClientId": download_id, "importMode": importMode}
            if not download_id:
                data.pop("downloadClientId")
            data = json.dumps(data)

        try:
            if section == "SickBeard":
                logger.debug("Opening URL: {0} with params: {1}".format(url, fork_params), section)
                s = requests.Session()
                if not apikey and username and password:
                    login = "{0}{1}:{2}{3}/login".format(protocol, host, port, web_root)
                    login_params = {'username': username, 'password': password}
                    r = s.get(login, verify=False, timeout=(30,60))
                    if r.status_code == 401 and r.cookies.get('_xsrf'):
                        login_params['_xsrf'] = r.cookies.get('_xsrf')
                    s.post(login, data=login_params, stream=True, verify=False, timeout=(30, 60))
                r = s.get(url, auth=(username, password), params=fork_params, stream=True, verify=False, timeout=(30, 1800))
            elif section == "NzbDrone":
                logger.debug("Opening URL: {0} with data: {1}".format(url, data), section)
                r = requests.post(url, data=data, headers=headers, stream=True, verify=False, timeout=(30, 1800))
        except requests.ConnectionError:
            logger.error("Unable to open URL: {0}".format(url), section)
            return [1, "{0}: Failed to post-process - Unable to connect to {1}".format(section, section)]

        if r.status_code not in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status {0}".format(r.status_code), section)
            return [1, "{0}: Failed to post-process - Server returned status {1}".format(section, r.status_code)]

        Success = False
        Queued = False
        Started = False
        if section == "SickBeard":
            if apikey:
                if r.json()['result'] == 'success':
                    Success = True
            else:
                for line in r.iter_lines():
                    if line:
                        logger.postprocess("{0}".format(line), section)
                        if "Moving file from" in line:
                            inputName = os.path.split(line)[1]
                        if "added to the queue" in line:
                            Queued = True
                        if "Processing succeeded" in line or "Successfully processed" in line:
                            Success = True

            if Queued:
                time.sleep(60)
        elif section == "NzbDrone":
            try:
                res = json.loads(r.content)
                scan_id = int(res['id'])
                logger.debug("Scan started with id: {0}".format(scan_id), section)
                Started = True
            except Exception as e:
                logger.warning("No scan id was returned due to: {0}".format(e), section)
                scan_id = None
                Started = False

        if status != 0 and delete_failed and not os.path.dirname(dirName) == dirName:
            logger.postprocess("Deleting failed files and folder {0}".format(dirName), section)
            rmDir(dirName)

        if Success:
            return [0, "{0}: Successfully post-processed {1}".format(section, inputName)]
        elif section == "NzbDrone" and Started:
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
            if self.CDH(url2, headers, section=section):
                logger.debug("The Scan command did not return status completed, but complete Download Handling is enabled. Passing back to {0}.".format(section), section)
                return [status, "{0}: Complete DownLoad Handling is enabled. Passing back to {1}".format(section, section)]
            else:
                logger.warning("The Scan command did not return a valid status. Renaming was not successful.", section)
                return [1, "{0}: Failed to post-process {1}".format(section, inputName)]
        else:
            return [1, "{0}: Failed to post-process - Returned log from {1} was not as expected.".format(section, section)]  # We did not receive Success confirmation.
