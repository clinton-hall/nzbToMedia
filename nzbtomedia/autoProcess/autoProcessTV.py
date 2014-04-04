import copy
import logging
import os
import socket
import urllib
import time
from lib import requests
from nzbtomedia.Transcoder import Transcoder
from nzbtomedia.nzbToMediaAutoFork import autoFork
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaSceneExceptions import process_all_exceptions
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, is_sample, flatten, getDirectorySize, delete

Logger = logging.getLogger()

class autoProcessTV:
    def processEpisode(self, dirName, nzbName=None, failed=False, clientAgent = "manual", inputCategory=None):
        if dirName is None:
            Logger.error("No directory was given!")
            return 1  # failure

        socket.setdefaulttimeout(int(config.NZBTOMEDIA_TIMEOUT))  #initialize socket timeout.

        Logger.info("Loading config from %s", config.CONFIG_FILE)

        status = int(failed)

        section = "SickBeard"
        host = config()[section][inputCategory]["host"]
        port = config()[section][inputCategory]["port"]
        username = config()[section][inputCategory]["username"]
        password = config()[section][inputCategory]["password"]

        try:
            ssl = int(config()[section][inputCategory]["ssl"])
        except:
            ssl = 0
        try:
            web_root = config()[section][inputCategory]["web_root"]
        except:
            web_root = ""
        try:
            watch_dir = config()[section][inputCategory]["watch_dir"]
        except:
            watch_dir = ""
        try:
            transcode = int(config()["Transcoder"]["transcode"])
        except:
            transcode = 0
        try:
            delete_failed = int(config()[section][inputCategory]["delete_failed"])
        except:
            delete_failed = 0
        try:
            delay = float(config()[section][inputCategory]["delay"])
        except:
            delay = 0
        try:
            TimePerGiB = int(config()[section][inputCategory]["TimePerGiB"])
        except:
            TimePerGiB = 60 # note, if using Network to transfer on 100Mbit LAN, expect ~ 600 MB/minute.
        try:
            SampleIDs = (config()["Extensions"]["SampleIDs"])
        except:
            SampleIDs = ['sample','-s.']
        try:
            nzbExtractionBy = config()[section][inputCategory]["nzbExtractionBy"]
        except:
            nzbExtractionBy = "Downloader"
        try:
            process_method = config()[section][inputCategory]["process_method"]
        except:
            process_method = None
        try:
            Torrent_NoLink = int(config()[section][inputCategory]["Torrent_NoLink"])
        except:
            Torrent_NoLink = 0


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

        # auto-detect fork type
        fork, params = autoFork(section, inputCategory)

        if fork not in config.SICKBEARD_TORRENT or (clientAgent in ['nzbget','sabnzbd'] and nzbExtractionBy != "Destination"):
            if nzbName:
                process_all_exceptions(nzbName.lower(), dirName)
                nzbName, dirName = convert_to_ascii(nzbName, dirName)

            # Now check if tv files exist in destination. Eventually extraction may be done here if nzbExtractionBy == TorrentToMedia
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
                flatten(dirName) # to make sure SickBeard can find the video (not in sub-folder)
            elif clientAgent == "manual":
                Logger.warning("No media files found in directory %s to manually process.", dirName)
                return 0  # Success (as far as this script is concerned)
            else:
                Logger.warning("No media files found in directory %s. Processing this as a failed download", dirName)
                status = int(1)
                failed = True

        dirSize = getDirectorySize(dirName) # get total directory size to calculate needed processing time.
        TIME_OUT = int(TimePerGiB) * dirSize # SickBeard needs to complete all moving and renaming before returning the log sequence via url.
        TIME_OUT += 60 # Add an extra minute for over-head/processing/metadata.
        socket.setdefaulttimeout(int(TIME_OUT)) #initialize socket timeout.

        # configure SB params to pass
        params['quiet'] = 1
        if nzbName is not None:
            params['nzbName'] = nzbName

        for param in copy.copy(params):
            if param == "failed":
                params[param] = failed

            if param in ["dirName", "dir"]:
                params[param] = dirName

            if param == "process_method":
                if fork in config.SICKBEARD_TORRENT and Torrent_NoLink == 1 and not clientAgent in ['nzbget','sabnzbd']: #use default SickBeard settings here.
                    del params[param]
                if process_method:
                    params[param] = process_method
                else:
                    del params[param]

        # delete any unused params so we don't pass them to SB by mistake
        [params.pop(k) for k,v in params.items() if v is None]

        if status == 0:
            Logger.info("The download succeeded. Sending process request to SickBeard's %s branch", fork)
        elif fork in config.SICKBEARD_FAILED:
            Logger.info("The download failed. Sending 'failed' process request to SickBeard's %s branch", fork)
        else:
            Logger.info("The download failed. SickBeard's %s branch does not handle failed downloads. Nothing to process", fork)
            if delete_failed and os.path.isdir(dirName) and not dirName in ['sys.argv[0]','/','']:
                Logger.info("Deleting directory: %s", dirName)
                delete(dirName)
            return 0 # Success (as far as this script is concerned)

        if status == 0 and transcode == 1: # only transcode successful downlaods
            result = Transcoder().Transcode_directory(dirName)
            if result == 0:
                Logger.debug("Transcoding succeeded for files in %s", dirName)
            else:
                Logger.warning("Transcoding failed for files in %s", dirName)

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        url = protocol + host + ":" + port + web_root + "/home/postprocess/processEpisode?" + urllib.urlencode(params)

        if clientAgent == "manual":delay = 0
        Logger.info("Waiting for %s seconds to allow SB to process newly extracted files", str(delay))

        time.sleep(delay)

        Logger.debug("Opening URL: %s", url)

        try:
            r = requests.get(url, auth=(username, password), stream=True)
        except requests.ConnectionError:
            Logger.exception("Unable to open URL")
            return 1 # failure

        for line in r.iter_lines():
            if line: Logger.info("%s", line)

        if status != 0 and delete_failed and not dirName in ['sys.argv[0]','/','']:
            delete(dirName)
        return 0 # Success
