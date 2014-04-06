import json
import logging
import os
import socket
from lib import requests
from nzbtomedia.Transcoder import Transcoder
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaSceneExceptions import process_all_exceptions
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, is_sample, flatten

Logger = logging.getLogger()

class autoProcessTVND:
    def processEpisode(self, dirName, nzbName=None, failed=False, clientAgent = "manual", inputCategory=None):
        if dirName is None:
            Logger.error("No directory was given!")
            return 1  # failure

        socket.setdefaulttimeout(int(config.NZBTOMEDIA_TIMEOUT))  #initialize socket timeout.

        Logger.info("Loading config from %s", config.CONFIG_FILE)

        status = int(failed)

        section = "NzbDrone"
        host = config()[section][inputCategory]["Host"]
        port = config()[section][inputCategory]["Port"]
        api_key = config()[section][inputCategory]["APIKey"]

        try:
            ssl = int(config()[section][inputCategory]["SSL"])
        except:
            ssl = 0
        try:
            web_root = config()[section][inputCategory]["WebRoot"]
        except:
            web_root = ""
        try:
            transcode = int(config()["Transcoder"]["transcode"])
        except:
            transcode = 0
        try:
            SampleIDs = (config()["Extensions"]["SampleIDs"])
        except:
            SampleIDs = ['sample','-s.']


        mediaContainer = (config()["Extensions"]["mediaExtensions"])
        minSampleSize = int(config()["Extensions"]["minSampleSize"])

        if not os.path.isdir(dirName) and os.path.isfile(dirName): # If the input directory is a file, assume single file download and split dir/name.
            dirName = os.path.split(os.path.normpath(dirName))[0]

        SpecificPath = os.path.join(dirName, str(nzbName))
        cleanName = os.path.splitext(SpecificPath)
        if cleanName[1] == ".nzb":
            SpecificPath = cleanName[0]
        if os.path.isdir(SpecificPath):
            dirName = SpecificPath

        # Confirm that the path contains videos and clean up.
        if nzbName:
            process_all_exceptions(nzbName.lower(), dirName)
            nzbName, dirName = convert_to_ascii(nzbName, dirName)

        # Now check if tv files exist in destination.
        video = int(0)
        for dirpath, dirnames, filenames in os.walk(dirName):
            for file in filenames:
                filePath = os.path.join(dirpath, file)
                fileExtension = os.path.splitext(file)[1]
                if fileExtension in mediaContainer:  # If the file is a video file
                    if is_sample(filePath, nzbName, minSampleSize, SampleIDs):
                        Logger.debug("Removing sample file: %s", filePath)
                        os.unlink(filePath)  # remove samples
                    else:
                        video = video + 1
        if video > 0:  # Check that a video exists. if not, assume failed.
            flatten(dirName) # to make sure NzbDrone can find the video (not in sub-folder)
        elif clientAgent == "manual":
            Logger.warning("No media files found in directory %s to manually process.", dirName)
            return 0  # Success (as far as this script is concerned)
        else:
            Logger.warning("No media files found in directory %s. Processing this as a failed download", dirName)
            status = int(1)
            failed = True

        if status == 0 and transcode == 1: # only transcode successful downlaods
            result = Transcoder().Transcode_directory(dirName)
            if result == 0:
                Logger.debug("Transcoding succeeded for files in %s", dirName)
            else:
                Logger.warning("Transcoding failed for files in %s", dirName)

        if status == 0:
            Logger.info("The download succeeded. Sending process request to NzbDrone")
        else:
            Logger.info("The download failed. Sending 'failed' process request to NzbDrone")

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        url = protocol + host + ":" + port + web_root + "/api/command"
        data = json.dumps({"name": "DownloadedEpisodesScan", "path": dirName})
        headers = {"X-Api-Key": api_key}

        Logger.debug("Opening URL: %s, with data %s and headers %s", url, data, headers)

        try:
            r = requests.post(url, data=data, headers=headers)
        except requests.ConnectionError:
            Logger.exception("Unable to open URL")
            return 1 # failure

        for line in r.iter_lines():
            if line: Logger.info("%s", line)

        return 0 # Success
