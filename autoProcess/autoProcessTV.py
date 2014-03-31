import sys
import urllib
import os
import ConfigParser
import logging
import shutil
import time
import socket
import copy

import Transcoder
from nzbToMediaEnv import *
from nzbToMediaUtil import *
from nzbToMediaSceneExceptions import process_all_exceptions
from autoSickBeardFork import autoFork

Logger = logging.getLogger()

class AuthURLOpener(urllib.FancyURLopener):
    def __init__(self, user, pw):
        self.username = user
        self.password = pw
        self.numTries = 0
        urllib.FancyURLopener.__init__(self)

    def prompt_user_passwd(self, host, realm):
        if self.numTries == 0:
            self.numTries = 1
            return (self.username, self.password)
        else:
            return ('', '')

    def openit(self, url):
        self.numTries = 0
        return urllib.FancyURLopener.open(self, url)

def delete(dirName):
    Logger.info("Deleting failed files and folder %s", dirName)
    try:
        shutil.rmtree(dirName, True)
    except:
        Logger.exception("Unable to delete folder %s", dirName)


def processEpisode(dirName, nzbName=None, failed=False, clientAgent=None, inputCategory=None):

    status = int(failed)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    config.read(configFilename)

    section = "SickBeard"
    if inputCategory != None and config.has_section(inputCategory):
        section = inputCategory

    watch_dir = ""
    host = config.get(section, "host")
    port = config.get(section, "port")
    username = config.get(section, "username")
    password = config.get(section, "password")

    try:
        ssl = int(config.get(section, "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config.get(section, "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    try:
        watch_dir = config.get(section, "watch_dir")
    except ConfigParser.NoOptionError:
        watch_dir = ""

    try:
        transcode = int(config.get("Transcoder", "transcode"))
    except (ConfigParser.NoOptionError, ValueError):
        transcode = 0

    try:
        delete_failed = int(config.get(section, "delete_failed"))
    except (ConfigParser.NoOptionError, ValueError):
        delete_failed = 0
    try:
        delay = float(config.get(section, "delay"))
    except (ConfigParser.NoOptionError, ValueError):
        delay = 0
    try:
        wait_for = int(config.get(section, "wait_for"))
    except (ConfigParser.NoOptionError, ValueError):
        wait_for = 5
    try:
        SampleIDs = (config.get("Extensions", "SampleIDs")).split(',')
    except (ConfigParser.NoOptionError, ValueError):
        SampleIDs = ['sample','-s.']
    try:
        nzbExtractionBy = config.get(section, "nzbExtractionBy")
    except (ConfigParser.NoOptionError, ValueError):
        nzbExtractionBy = "Downloader"

    try:
        process_method = config.get(section, "process_method")
    except ConfigParser.NoOptionError:
        process_method = None

    TimeOut = 60 * int(wait_for) # SickBeard needs to complete all moving and renaming before returning the log sequence via url.
    socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

    mediaContainer = (config.get("Extensions", "mediaExtensions")).split(',')
    minSampleSize = int(config.get("Extensions", "minSampleSize"))

    if not os.path.isdir(dirName) and os.path.isfile(dirName): # If the input directory is a file, assume single file download and split dir/name.
        dirName = os.path.split(os.path.normpath(dirName))[0]

    SpecificPath = os.path.join(dirName, nzbName)
    cleanName = os.path.splitext(SpecificPath)
    if cleanName[1] == ".nzb":
        SpecificPath = cleanName[0]
    if os.path.isdir(SpecificPath):
        dirName = SpecificPath

    # auto-detect fork type
    fork, params = autoFork()

    if nzbName != "Manual Run" and (not fork in SICKBEARD_TORRENT or (clientAgent in ['nzbget','sabnzbd'] and not nzbExtractionBy == "Destination")):
        process_all_exceptions(nzbName.lower(), dirName)
        nzbName, dirName = converto_to_ascii(nzbName, dirName)

        # Now check if movie files exist in destination. Eventually extraction may be done here if nzbExtractionBy == TorrentToMedia
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
        else:
            Logger.warning("No media files found in directory %s. Processing this as a failed download", dirName)
            status = int(1)
            failed = True

    if watch_dir != "" and (not host in ['localhost', '127.0.0.1'] or nzbName == "Manual Run"):
        dirName = watch_dir

    # don't have sickbeard display any output
    params['quiet'] = 1

    for param in copy.copy(params):
        if param is "failed":
            params[param] = failed

        if param is "dirName":
            params[param] = dirName

        if param is "dir":
            params[param] = dirName

        if param is "process_method":
            if process_method:
                params[param] = process_method
            else:
                del params[param]

        if param is "process":
            params["process"] = None

        if param is "process_method":
            params["process_method"] = None

    if nzbName != None:
        params['nzbName'] = nzbName

    if status == 0:
        Logger.info("The download succeeded. Sending process request to SickBeard's %s branch", fork)
    elif fork in SICKBEARD_FAILED:
        Logger.info("The download failed. Sending 'failed' process request to SickBeard's %s branch", fork)
    else:
        Logger.info("The download failed. SickBeard's %s branch does not handle failed downloads. Nothing to process", fork)
        if delete_failed and os.path.isdir(dirName) and not dirName in ['sys.argv[0]','/','']:
            Logger.info("Deleting directory: %s", dirName)
            delete(dirName)
        return 0 # Success (as far as this script is concerned)

    if status == 0 and transcode == 1: # only transcode successful downlaods
        result = Transcoder.Transcode_directory(dirName)
        if result == 0:
            Logger.debug("Transcoding succeeded for files in %s", dirName)
        else:
            Logger.warning("Transcoding failed for files in %s", dirName)

    myOpener = AuthURLOpener(username, password)

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + host + ":" + port + web_root + "/home/postprocess/processEpisode?" + urllib.urlencode(params)

    Logger.info("Waiting for %s seconds to allow SB to process newly extracted files", str(delay))

    time.sleep(delay)

    Logger.debug("Opening URL: %s", url)

    try:
        urlObj = myOpener.openit(url)
    except:
        Logger.exception("Unable to open URL")
        return 1 # failure

    result = urlObj.readlines()
    for line in result:
        Logger.info("%s", line.rstrip())
    if status != 0 and delete_failed and not dirName in ['sys.argv[0]','/','']:
        delete(dirName)
    return 0 # Success
