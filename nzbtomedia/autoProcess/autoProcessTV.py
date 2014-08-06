import copy
import os
import time
import errno
import requests
import json
import nzbtomedia

from nzbtomedia.nzbToMediaAutoFork import autoFork
from nzbtomedia.nzbToMediaSceneExceptions import process_all_exceptions
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, flatten, rmDir, listMediaFiles, remoteDir, import_subs, server_responding
from nzbtomedia import logger
from nzbtomedia.transcoder import transcoder

class autoProcessTV:
    def numMissing(self, url1, params, headers):
        r = None
        missing = 0
        try:
            r = requests.get(url1, params=params, headers=headers, stream=True, verify=False)
        except requests.ConnectionError:
            logger.error("Unable to open URL: %s" % (url1), section)
            return missing
        if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status %s" % (str(r.status_code)), section)
        else:
            try:
                res = json.loads(r.content)
                missing = int(res['totalRecords'])
            except:
                pass
        return missing

    def processEpisode(self, section, dirName, inputName=None, failed=False, clientAgent = "manual", inputCategory=None):
        host = nzbtomedia.CFG[section][inputCategory]["host"]
        port = nzbtomedia.CFG[section][inputCategory]["port"]
        try:
            ssl = int(nzbtomedia.CFG[section][inputCategory]["ssl"])
        except:
            ssl = 0
        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"
        try:
            web_root = nzbtomedia.CFG[section][inputCategory]["web_root"]
        except:
            web_root = ""
        if not server_responding("%s%s:%s%s" % (protocol,host,port,web_root)):
            logger.error("Server did not respond. Exiting", section)
            return [1, "%s: Failed to post-process - %s did not respond." % (section, section) ]

        # auto-detect correct fork
        fork, fork_params = autoFork(section, inputCategory)

        try:
            username = nzbtomedia.CFG[section][inputCategory]["username"]
            password = nzbtomedia.CFG[section][inputCategory]["password"]
        except:
            username = ""
            password = ""
        try:
            apikey = nzbtomedia.CFG[section][inputCategory]["apikey"]
        except:
            apikey = ""
        try:
            delete_failed = int(nzbtomedia.CFG[section][inputCategory]["delete_failed"])
        except:
            delete_failed = 0
        try:
            nzbExtractionBy = nzbtomedia.CFG[section][inputCategory]["nzbExtractionBy"]
        except:
            nzbExtractionBy = "Downloader"
        try:
            process_method = nzbtomedia.CFG[section][inputCategory]["process_method"]
        except:
            process_method = None
        try:
            remote_path = int(nzbtomedia.CFG[section][inputCategory]["remote_path"])
        except:
            remote_path = 0
        try:
            wait_for = int(nzbtomedia.CFG[section][inputCategory]["wait_for"])
        except:
            wait_for = 2
        try:
            force = int(nzbtomedia.CFG[section][inputCategory]["force"])
        except:
            force = 0
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
        elif clientAgent == "manual" and not listMediaFiles(dirName, media=True, audio=False, meta=False, archives=True):
                logger.warning("No media files found in directory %s to manually process." % (dirName), section)
                return [0, ""]   # Success (as far as this script is concerned)

        if fork not in nzbtomedia.SICKBEARD_TORRENT or (clientAgent in ['nzbget','sabnzbd'] and nzbExtractionBy != "Destination"):
            if inputName:
                process_all_exceptions(inputName.lower(), dirName)
                inputName, dirName = convert_to_ascii(inputName, dirName)

            # Now check if tv files exist in destination. 
            if listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False):  # Check that a video exists. if not, assume failed.
                flatten(dirName) # to make sure SickBeard can find the video (not in sub-folder)
            elif listMediaFiles(dirName, media=False, audio=False, meta=False, archives=True) and extract:
                logger.debug('Checking for archives to extract in directory: %s' % (dirName))
                nzbtomedia.extractFiles(dirName)
                inputName, dirName = convert_to_ascii(inputName, dirName)
                good_files = 0
                num_files = 0
                for video in listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False):
                    num_files += 1
                    if transcoder.isVideoGood(video, status):
                        good_files += 1
                        import_subs(video)
                if num_files > 0 and good_files == num_files:
                    logger.info('Found Valid Videos. Setting status Success')
                    status = 0
                    failed = 0

            if listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False):  # Check that a video exists. if not, assume failed.
                flatten(dirName) 
            elif clientAgent == "manual":
                logger.warning("No media files found in directory %s to manually process." % (dirName), section)
                return [0, ""]   # Success (as far as this script is concerned)
            else:
                logger.warning("No media files found in directory %s. Processing this as a failed download" % (dirName), section)
                status = 1
                failed = 1

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

        # delete any unused params so we don't pass them to SB by mistake
        [fork_params.pop(k) for k,v in fork_params.items() if v is None]

        if status == 0:
            logger.postprocess("SUCCESS: The download succeeded, sending a post-process request", section)
        else:
            if fork in nzbtomedia.SICKBEARD_FAILED or section == "NzbDrone":
                logger.postprocess("FAILED: The download failed. Sending 'failed' process request to %s branch" % (fork), section)
            else:
                logger.postprocess("FAILED: The download failed. %s branch does not handle failed downloads. Nothing to process" % (fork), section)
                if delete_failed and os.path.isdir(dirName) and not os.path.dirname(dirName) == dirName:
                    logger.postprocess("Deleting failed files and folder %s" % (dirName), section)
                    rmDir(dirName)
                return [1, "%s: Failed to post-process. %s does not support failed downloads" % (section, section) ] # Return as failed to flag this in the downloader.

        if status == 0 and nzbtomedia.TRANSCODE == 1: # only transcode successful downlaods
            result, newDirName = transcoder.Transcode_directory(dirName)
            if result == 0:
                logger.debug("SUCCESS: Transcoding succeeded for files in %s" % (dirName), section)
                dirName = newDirName
            else:
                logger.warning("FAILED: Transcoding failed for files in %s" % (dirName), section)

        url = None
        if section == "SickBeard":
            url = "%s%s:%s%s/home/postprocess/processEpisode" % (protocol,host,port,web_root)
        elif section == "NzbDrone":
            url = "%s%s:%s%s/api/command" % (protocol, host, port, web_root)
            url1 = "%s%s:%s%s/api/missing" % (protocol, host, port, web_root)
            headers = {"X-Api-Key": apikey}
            params = {'sortKey': 'series.title', 'page': 1, 'pageSize': 1, 'sortDir': 'asc'}
            if remote_path:
                logger.debug("remote_path: %s" % (remoteDir(dirName)),section)
                data = json.dumps({"name": "DownloadedEpisodesScan", "path": remoteDir(dirName)})
            else:
                logger.debug("path: %s" % (dirName),section)
                data = json.dumps({"name": "DownloadedEpisodesScan", "path": dirName})

        try:
            if section == "SickBeard":
                logger.debug("Opening URL: %s with params: %s" % (url, str(fork_params)), section)
                r = None
                r = requests.get(url, auth=(username, password), params=fork_params, stream=True, verify=False)
            elif section == "NzbDrone":
                start_numMissing = self.numMissing(url1, params, headers)  # get current number of outstanding eppisodes.
                logger.debug("Opening URL: %s with data: %s" % (url, str(data)), section)
                r = None
                r = requests.post(url, data=data, headers=headers, stream=True, verify=False)
        except requests.ConnectionError:
            logger.error("Unable to open URL: %s" % (url), section)
            return [1, "%s: Failed to post-process - Unable to connect to %s" % (section, section) ]

        if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status %s" % (str(r.status_code)), section)
            return [1, "%s: Failed to post-process - Server returned status %s" % (section, str(r.status_code)) ]

        Success = False
        Started = False
        for line in r.iter_lines():
            if line: 
                logger.postprocess("%s" % (line), section)
                if section == "SickBeard" and "Processing succeeded" in line:
                    Success = True
                elif section == "NzbDrone" and "stateChangeTime" in line:
                    Started = True

        if status != 0 and delete_failed and not os.path.dirname(dirName) == dirName:
            logger.postprocess("Deleting failed files and folder %s" % (dirName),section)
            rmDir(dirName)

        if Success:
            return [0, "%s: Successfully post-processed %s" % (section, inputName) ]
        elif section == "NzbDrone" and Started:
            n = 0
            current_numMissing = start_numMissing
            while n < 6:  # set up wait_for minutes of no change in numMissing.
                time.sleep(10 * wait_for)
                if not os.path.exists(dirName):
                    break
                new_numMissing = self.numMissing(url1, params, headers)
                if new_numMissing == current_numMissing:  # nothing processed since last call
                    n += 1
                else:
                    n = 0
                    current_numMissing = new_numMissing  # reset counter and start loop again with this many missing.

            if not os.path.exists(dirName):
                logger.debug("The directory %s has been removed. Renaming was successful." % (dirName), section)
                return [0, "%s: Successfully post-processed %s" % (section, inputName) ]
            elif current_numMissing < start_numMissing:
                logger.debug(
                "The number of missing episodes changes from %s to %s and then remained the same for %s minutes. Consider this successful" % 
                (str(start_numMissing), str(current_numMissing), str(wait_for)), section)
                return [0, "%s: Successfully post-processed %s" % (section, inputName) ]
            else:
                # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resume seeding now.
                logger.warning(
                "The number of missing episodes: %s does not appear to have changed status after %s minutes, Please check your logs." % 
                (str(start_numMissing), str(wait_for)), section)
                return [1, "%s: Failed to post-process - No change in wanted status" % (section) ]
        else:
            return [1, "%s: Failed to post-process - Returned log from %s was not as expected." % (section, section) ]  # We did not receive Success confirmation.
