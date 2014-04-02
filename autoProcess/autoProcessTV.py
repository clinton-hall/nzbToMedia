import urllib
import logging
import copy

import Transcoder
from nzbToMediaSceneExceptions import process_all_exceptions
from autoProcess.autoSickBeardFork import autoFork
from nzbToMediaEnv import *
from nzbToMediaUtil import *

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


def processEpisode(dirName, nzbName=None, failed=False, clientAgent = "manual", inputCategory=None):

    status = int(failed)

    Logger.info("Loading config from %s", CONFIG_FILE)

    if not config():
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    section = "SickBeard"
    if inputCategory != None and config().has_section(inputCategory):
        section = inputCategory

    host = config().get(section, "host")
    port = config().get(section, "port")
    username = config().get(section, "username")
    password = config().get(section, "password")

    try:
        ssl = int(config().get(section, "ssl"))
    except (config.NoOptionError, ValueError):
        ssl = 0
    try:
        web_root = config().get(section, "web_root")
    except config.NoOptionError:
        web_root = ""
    try:
        watch_dir = config().get(section, "watch_dir")
    except config.NoOptionError:
        watch_dir = ""
    try:
        transcode = int(config().get("Transcoder", "transcode"))
    except (config.NoOptionError, ValueError):
        transcode = 0
    try:
        delete_failed = int(config().get(section, "delete_failed"))
    except (config.NoOptionError, ValueError):
        delete_failed = 0
    try:
        delay = float(config().get(section, "delay"))
    except (config.NoOptionError, ValueError):
        delay = 0
    try:
        TimePerGiB = int(config().get(section, "TimePerGiB"))
    except (config.NoOptionError, ValueError):
        TimePerGiB = 60 # note, if using Network to transfer on 100Mbit LAN, expect ~ 600 MB/minute.
    try:
        SampleIDs = (config().get("Extensions", "SampleIDs")).split(',')
    except (config.NoOptionError, ValueError):
        SampleIDs = ['sample','-s.']
    try:
        nzbExtractionBy = config().get(section, "nzbExtractionBy")
    except (config.NoOptionError, ValueError):
        nzbExtractionBy = "Downloader"
    try:
        process_method = config().get(section, "process_method")
    except config.NoOptionError:
        process_method = None

    # configure dirName for manual run
    try:
        if dirName == 'Manual Run':
            delay = 0
            if watch_dir != "" and (not host in ['localhost', '127.0.0.1']):
                dirName = watch_dir
            else:
                sbCategory = (config().get("SickBeard", "sbCategory")).split(',')  # tv
                dirName = os.path.join(config().get("Torrent", "outputDirectory"), sbCategory[0])

            # check if path is valid
            if not os.path.exists(dirName):
                return 1  # failure
    except config.NoOptionError:
        return 1  # failure

    mediaContainer = (config().get("Extensions", "mediaExtensions")).split(',')
    minSampleSize = int(config().get("Extensions", "minSampleSize"))

    if not os.path.isdir(dirName) and os.path.isfile(dirName): # If the input directory is a file, assume single file download and split dir/name.
        dirName = os.path.split(os.path.normpath(dirName))[0]

    if nzbName:
        SpecificPath = os.path.join(dirName, str(nzbName))
    else:
        SpecificPath = dirName

    cleanName = os.path.splitext(SpecificPath)
    if cleanName[1] == ".nzb":
        SpecificPath = cleanName[0]
    if os.path.isdir(SpecificPath):
        dirName = SpecificPath

    # auto-detect fork type
    fork, params = autoFork()

    if fork not in SICKBEARD_TORRENT or (clientAgent in ['nzbget','sabnzbd'] and nzbExtractionBy != "Destination"):
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
    TimeOut = int(TimePerGiB) * dirSize # SickBeard needs to complete all moving and renaming before returning the log sequence via url.
    TimeOut += 60 # Add an extra minute for over-head/processing/metadata.
    socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

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
            if process_method:
                params[param] = process_method
            else:
                del params[param]

    # delete any unused params so we don't pass them to SB by mistake
    [params.pop(k) for k,v in params.items() if v is None]

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
