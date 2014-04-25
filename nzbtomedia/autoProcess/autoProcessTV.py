import copy
import os
import requests
import nzbtomedia

from nzbtomedia.nzbToMediaAutoFork import autoFork
from nzbtomedia.nzbToMediaSceneExceptions import process_all_exceptions
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, flatten, rmDir, listMediaFiles
from nzbtomedia import logger
from nzbtomedia.transcoder import transcoder

class autoProcessTV:
    def processEpisode(self, section, dirName, inputName=None, failed=False, clientAgent = "manual", inputCategory=None):
        # auto-detect correct fork
        fork, fork_params = autoFork(inputCategory)

        # Check video files for corruption
        status = int(failed)
        for video in listMediaFiles(dirName):
            if not transcoder.isVideoGood(video):
                status = 1

        host = nzbtomedia.CFG[section][inputCategory]["host"]
        port = nzbtomedia.CFG[section][inputCategory]["port"]
        username = nzbtomedia.CFG[section][inputCategory]["username"]
        password = nzbtomedia.CFG[section][inputCategory]["password"]

        try:
            apikey = nzbtomedia.CFG[section][inputCategory]["apikey"]
        except:
            apikey = ""
        try:
            ssl = int(nzbtomedia.CFG[section][inputCategory]["ssl"])
        except:
            ssl = 0
        try:
            web_root = nzbtomedia.CFG[section][inputCategory]["web_root"]
        except:
            web_root = ""
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
            remote_path = nzbtomedia.CFG[section][inputCategory]["remote_path"]
        except:
            remote_path = None

        if not os.path.isdir(dirName) and os.path.isfile(dirName): # If the input directory is a file, assume single file download and split dir/name.
            dirName = os.path.split(os.path.normpath(dirName))[0]

        SpecificPath = os.path.join(dirName, str(inputName))
        cleanName = os.path.splitext(SpecificPath)
        if cleanName[1] == ".nzb":
            SpecificPath = cleanName[0]
        if os.path.isdir(SpecificPath):
            dirName = SpecificPath

        if fork not in nzbtomedia.SICKBEARD_TORRENT or (clientAgent in ['nzbget','sabnzbd'] and nzbExtractionBy != "Destination"):
            if inputName:
                process_all_exceptions(inputName.lower(), dirName)
                inputName, dirName = convert_to_ascii(inputName, dirName)

            # Now check if tv files exist in destination. Eventually extraction may be done here if nzbExtractionBy == TorrentToMedia
            if listMediaFiles(dirName):  # Check that a video exists. if not, assume failed.
                flatten(dirName) # to make sure SickBeard can find the video (not in sub-folder)
            elif clientAgent == "manual":
                logger.warning("No media files found in directory %s to manually process." % (dirName), section)
                return 0  # Success (as far as this script is concerned)
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
                    fork_params[param] = os.path.join(remote_path, os.path.basename(dirName))

            if param == "process_method":
                if process_method:
                    fork_params[param] = process_method
                else:
                    del fork_params[param]

        # delete any unused params so we don't pass them to SB by mistake
        [fork_params.pop(k) for k,v in fork_params.items() if v is None]

        if status == 0:
            logger.postprocess("SUCCESS: The download succeeded, sending a post-process request", section)
        else:
            if fork in nzbtomedia.SICKBEARD_FAILED:
                logger.postprocess("FAILED: The download failed. Sending 'failed' process request to %s branch" % (fork), section)
            else:
                logger.postprocess("FAILED: The download failed. %s branch does not handle failed downloads. Nothing to process" % (fork), section)
                if delete_failed and os.path.isdir(dirName) and not os.path.dirname(dirName) == dirName:
                    logger.postprocess("Deleting failed files and folder %s" % (dirName), section)
                    rmDir(dirName)
                return 0 # Success (as far as this script is concerned)

        if status == 0 and nzbtomedia.TRANSCODE == 1: # only transcode successful downlaods
            result = transcoder.Transcode_directory(dirName)
            if result == 0:
                logger.debug("SUCCESS: Transcoding succeeded for files in %s" % (dirName), section)
            else:
                logger.warning("FAILED: Transcoding failed for files in %s" % (dirName), section)

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        url = None
        if section == "SickBeard":
            url = "%s%s:%s%s/home/postprocess/processEpisode" % (protocol,host,port,web_root)
        elif section == "NzbDrone":
            url = "%s%s:%s%s/api/command" % (protocol, host, port, web_root)

        logger.debug("Opening URL: %s" % (url),section)

        try:
            r = None
            if section == "SickBeard":
                r = requests.get(url, auth=(username, password), params=fork_params, stream=True, verify=False)
            elif section == "NzbDrone":
                params = {"name": "DownloadedEpisodesScan", "path": dirName}
                headers = {"X-Api-Key": apikey}
                r = requests.get(url, params=params, headers=headers, stream=True, verify=False)
        except requests.ConnectionError:
            logger.error("Unable to open URL: %s" % (url), section)
            return 1 # failure

        for line in r.iter_lines():
            if line: logger.postprocess("%s" % (line), section)

        if status != 0 and delete_failed and not os.path.dirname(dirName) == dirName:
            logger.postprocess("Deleting failed files and folder %s" % (dirName),section)
            rmDir(dirName)
        return 0 # Success
