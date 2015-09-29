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

class autoProcessTV:
    def command_complete(self, url, params, headers, section):
        r = None
        try:
            r = requests.get(url, params=params, headers=headers, stream=True, verify=False, timeout=(30, 60))
        except requests.ConnectionError:
            logger.error("Unable to open URL: %s" % (url1), section)
            return None
        if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status %s" % (str(r.status_code)), section)
            return None
        else:
            try:
                res = json.loads(r.content)
                return res['state']
            except:
                logger.error("%s did not return expected json data." % section, section)
                return None

    def CDH(self, url2, headers):
        r = None
        try:
            r = requests.get(url2, params={}, headers=headers, stream=True, verify=False, timeout=(30, 60))
        except requests.ConnectionError:
            logger.error("Unable to open URL: %s" % (url2), section)
            return False
        if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status %s" % (str(r.status_code)), section)
            return False
        else:
            try:
                res = json.loads(r.content)
                return res["enableCompletedDownloadHandling"]
            except:
                return False

    def processEpisode(self, section, dirName, inputName=None, failed=False, clientAgent = "manual", download_id=None, inputCategory=None, failureLink=None):
        host = core.CFG[section][inputCategory]["host"]
        port = core.CFG[section][inputCategory]["port"]
        try:
            ssl = int(core.CFG[section][inputCategory]["ssl"])
        except:
            ssl = 0
        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"
        try:
            web_root = core.CFG[section][inputCategory]["web_root"]
        except:
            web_root = ""
        if not server_responding("%s%s:%s%s" % (protocol,host,port,web_root)):
            logger.error("Server did not respond. Exiting", section)
            return [1, "%s: Failed to post-process - %s did not respond." % (section, section) ]

        # auto-detect correct fork
        fork, fork_params = autoFork(section, inputCategory)

        try:
            username = core.CFG[section][inputCategory]["username"]
            password = core.CFG[section][inputCategory]["password"]
        except:
            username = ""
            password = ""
        try:
            apikey = core.CFG[section][inputCategory]["apikey"]
        except:
            apikey = ""
        try:
            delete_failed = int(core.CFG[section][inputCategory]["delete_failed"])
        except:
            delete_failed = 0
        try:
            nzbExtractionBy = core.CFG[section][inputCategory]["nzbExtractionBy"]
        except:
            nzbExtractionBy = "Downloader"
        try:
            process_method = core.CFG[section][inputCategory]["process_method"]
        except:
            process_method = None
        try:
            remote_path = int(core.CFG[section][inputCategory]["remote_path"])
        except:
            remote_path = 0
        try:
            wait_for = int(core.CFG[section][inputCategory]["wait_for"])
        except:
            wait_for = 2
        try:
            force = int(core.CFG[section][inputCategory]["force"])
        except:
            force = 0
        try:
            delete_on = int(core.CFG[section][inputCategory]["delete_on"])
        except:
            delete_on = 0
        try:
            extract = int(section[inputCategory]["extract"])
        except:
            extract = 0

        if not os.path.isdir(dirName) and os.path.isfile(dirName): # If the input directory is a file, assume single file download and split dir/name.
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
        except OSError, e:
            # Re-raise the error if it wasn't about the directory not existing
            if e.errno != errno.EEXIST:
                raise

        if fork not in core.SICKBEARD_TORRENT or (clientAgent in ['nzbget','sabnzbd'] and nzbExtractionBy != "Destination"):
            if inputName:
                process_all_exceptions(inputName, dirName)
                inputName, dirName = convert_to_ascii(inputName, dirName)

            # Now check if tv files exist in destination. 
            if not listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False):
                if listMediaFiles(dirName, media=False, audio=False, meta=False, archives=True) and extract:
                    logger.debug('Checking for archives to extract in directory: %s' % (dirName))
                    core.extractFiles(dirName)
                    inputName, dirName = convert_to_ascii(inputName, dirName)

            if listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False):  # Check that a video exists. if not, assume failed.
                flatten(dirName) 
            
        # Check video files for corruption
        status = int(failed)
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
                if os.environ.has_key('NZBOP_VERSION') and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
                    print('[NZB] MARK=BAD')
                if failureLink:
                    failureLink = failureLink + '&corrupt=true'
        elif clientAgent == "manual":
            logger.warning("No media files found in directory %s to manually process." % (dirName), section)
            return [0, ""]   # Success (as far as this script is concerned)
        else:
            logger.warning("No media files found in directory %s. Processing this as a failed download" % (dirName), section)
            status = 1
            failed = 1
            if os.environ.has_key('NZBOP_VERSION') and os.environ['NZBOP_VERSION'][0:5] >= '14.0':
                print('[NZB] MARK=BAD')

        if status == 0 and core.TRANSCODE == 1: # only transcode successful downloads
            result, newDirName = transcoder.Transcode_directory(dirName)
            if result == 0:
                logger.debug("SUCCESS: Transcoding succeeded for files in %s" % (dirName), section)
                dirName = newDirName
            else:
                logger.error("FAILED: Transcoding failed for files in %s" % (dirName), section)
                return [1, "%s: Failed to post-process - Transcoding failed" % (section) ]

        # configure SB params to pass
        fork_params['quiet'] = 1
        if inputName is not None:
            fork_params['nzbName'] = inputName

        for param in copy.copy(fork_params):
            if param == "failed":
                fork_params[param] = failed

            if param in ["dirName", "dir"]:
                fork_params[param] = dirName
                if remote_path:
                    fork_params[param] = remoteDir(dirName)

            if param == "process_method":
                if process_method:
                    fork_params[param] = process_method
                else:
                    del fork_params[param]

            if param == "force":
                if force:
                    fork_params[param] = force
                else:
                    del fork_params[param]

            if param == "delete_on":
                if delete_on:
                    fork_params[param] = delete_on
                else:
                    del fork_params[param]

        # delete any unused params so we don't pass them to SB by mistake
        [fork_params.pop(k) for k,v in fork_params.items() if v is None]

        if status == 0:
            logger.postprocess("SUCCESS: The download succeeded, sending a post-process request", section)
        else:
            if failureLink:
                reportNzb(failureLink, clientAgent)
            if fork in core.SICKBEARD_FAILED:
                logger.postprocess("FAILED: The download failed. Sending 'failed' process request to %s branch" % (fork), section)
            elif section == "NzbDrone":
                logger.postprocess("FAILED: The download failed. Sending failed download to %s for CDH processing" % (fork), section)
                return [1, "%s: Downlaod Failed. Sending back to %s" % (section, section) ] # Return as failed to flag this in the downloader.
            else:
                logger.postprocess("FAILED: The download failed. %s branch does not handle failed downloads. Nothing to process" % (fork), section)
                if delete_failed and os.path.isdir(dirName) and not os.path.dirname(dirName) == dirName:
                    logger.postprocess("Deleting failed files and folder %s" % (dirName), section)
                    rmDir(dirName)
                return [1, "%s: Failed to post-process. %s does not support failed downloads" % (section, section) ] # Return as failed to flag this in the downloader.

        url = None
        if section == "SickBeard":
            url = "%s%s:%s%s/home/postprocess/processEpisode" % (protocol,host,port,web_root)
        elif section == "NzbDrone":
            url = "%s%s:%s%s/api/command" % (protocol, host, port, web_root)
            url2 = "%s%s:%s%s/api/config/downloadClient" % (protocol, host, port, web_root)
            headers = {"X-Api-Key": apikey}
            params = {'sortKey': 'series.title', 'page': 1, 'pageSize': 1, 'sortDir': 'asc'}
            if remote_path:
                logger.debug("remote_path: %s" % (remoteDir(dirName)),section)
                data = {"name": "DownloadedEpisodesScan", "path": remoteDir(dirName), "downloadClientId": download_id}
            else:
                logger.debug("path: %s" % (dirName),section)
                data = {"name": "DownloadedEpisodesScan", "path": dirName, "downloadClientId": download_id}
            if not download_id:
                data.pop("downloadClientId")
            data = json.dumps(data)
                
        try:
            if section == "SickBeard":
                logger.debug("Opening URL: %s with params: %s" % (url, str(fork_params)), section)
                r = None
                s = requests.Session()
                login = "%s%s:%s%s/login" % (protocol,host,port,web_root)
                login_params = {'username': username, 'password': password}
                s.post(login, data=login_params, stream=True, verify=False, timeout=(30, 60))
                r = s.get(url, auth=(username, password), params=fork_params, stream=True, verify=False, timeout=(30, 1800))
            elif section == "NzbDrone":
                logger.debug("Opening URL: %s with data: %s" % (url, str(data)), section)
                r = None
                r = requests.post(url, data=data, headers=headers, stream=True, verify=False, timeout=(30, 1800))
        except requests.ConnectionError:
            logger.error("Unable to open URL: %s" % (url), section)
            return [1, "%s: Failed to post-process - Unable to connect to %s" % (section, section) ]

        if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status %s" % (str(r.status_code)), section)
            return [1, "%s: Failed to post-process - Server returned status %s" % (section, str(r.status_code)) ]

        Success = False
        Started = False
        if section == "SickBeard":
            for line in r.iter_lines():
                if line: 
                    logger.postprocess("%s" % (line), section)
                    if "Processing succeeded" in line or "Successfully processed" in line:
                        Success = True
        elif section == "NzbDrone":
            try:
                res = json.loads(r.content)
                scan_id = int(res['id'])
                logger.debug("Scan started with id: %s" % (str(scan_id)), section)
                Started = True
            except Exception as e:
                logger.warning("No scan id was returned due to: %s" % (e), section)
                scan_id = None
                Started = False

        if status != 0 and delete_failed and not os.path.dirname(dirName) == dirName:
            logger.postprocess("Deleting failed files and folder %s" % (dirName),section)
            rmDir(dirName)

        if Success:
            return [0, "%s: Successfully post-processed %s" % (section, inputName) ]
        elif section == "NzbDrone" and Started:
            n = 0
            params = {}
            url = url + "/" + str(scan_id)
            while n < 6:  # set up wait_for minutes to see if command completes..
                time.sleep(10 * wait_for)
                command_status = self.command_complete(url, params, headers, section)
                if command_status and command_status in ['completed', 'failed']:    
                     break
                n += 1
            if command_status:
                logger.debug("The Scan command return status: %s" % (command_status), section)
            if not os.path.exists(dirName):
                logger.debug("The directory %s has been removed. Renaming was successful." % (dirName), section)
                return [0, "%s: Successfully post-processed %s" % (section, inputName) ]
            elif command_status and command_status in ['completed']:
                logger.debug("The Scan command has completed successfully. Renaming was successful.", section)
                return [0, "%s: Successfully post-processed %s" % (section, inputName) ]
            elif command_status and command_status in ['failed']:
                logger.debug("The Scan command has failed. Renaming was not successful.", section)
                #return [1, "%s: Failed to post-process %s" % (section, inputName) ]
            if self.CDH(url2, headers):
                logger.debug("The Scan command did not return status completed, but complete Download Handling is enabled. Passing back to %s." % (section), section)
                return [status, "%s: Complete DownLoad Handling is enabled. Passing back to %s" % (section, section) ] 
            else:
                logger.warning("The Scan command did not return a valid status. Renaming was not successful.", section)
                return [1, "%s: Failed to post-process %s" % (section, inputName) ]
        else:
            return [1, "%s: Failed to post-process - Returned log from %s was not as expected." % (section, section) ]  # We did not receive Success confirmation.
