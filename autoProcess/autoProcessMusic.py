import urllib
import datetime
import logging

from nzbToMediaEnv import *
from nzbToMediaUtil import *


Logger = logging.getLogger()

def process(dirName, nzbName=None, status=0, inputCategory=None):

    status = int(status)


    Logger.info("Loading config from %s", CONFIG_FILE)

    if not config():
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure



    section = "HeadPhones"
    if inputCategory != None and config().has_section(inputCategory):
        section = inputCategory

    host = config().get(section, "host")
    port = config().get(section, "port")
    apikey = config().get(section, "apikey")
    delay = float(config().get(section, "delay"))

    try:
        ssl = int(config().get(section, "ssl"))
    except (config.NoOptionError, ValueError):
        ssl = 0
    try:
        web_root = config().get(section, "web_root")
    except config.NoOptionError:
        web_root = ""
    try:
        TimePerGiB = int(config().get(section, "TimePerGiB"))
    except (config.NoOptionError, ValueError):
        TimePerGiB = 60 # note, if using Network to transfer on 100Mbit LAN, expect ~ 600 MB/minute.
    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    # don't delay when we are calling this script manually.
    if nzbName == "Manual Run":
        delay = 0

    nzbName, dirName = convert_to_ascii(nzbName, dirName)

    dirSize = getDirectorySize(dirName) # get total directory size to calculate needed processing time.
    TimeOut = int(TimePerGiB) * dirSize # HeadPhones needs to complete all moving/transcoding and renaming before returning the status.
    TimeOut += 60 # Add an extra minute for over-head/processing/metadata.
    socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

    baseURL = protocol + host + ":" + port + web_root + "/api?apikey=" + apikey + "&cmd="

    if status == 0:
        command = "forceProcess"

        url = baseURL + command

        Logger.info("Waiting for %s seconds to allow HeadPhones to process newly extracted files", str(delay))

        time.sleep(delay)

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = urllib.urlopen(url)
        except:
            Logger.exception("Unable to open URL")
            return 1 # failure

        result = urlObj.readlines()
        Logger.info("HeadPhones returned %s", result)
        if result[0] == "OK":
            Logger.info("%s started on HeadPhones for %s", command, nzbName)
        else:
            Logger.error("%s has NOT started on HeadPhones for %s. Exiting", command, nzbName)
            return 1 # failure
            
    else:
        Logger.info("The download failed. Nothing to process")
        return 0 # Success (as far as this script is concerned)

    if nzbName == "Manual Run":
        return 0 # success

    # we will now wait 1 minutes for this album to be processed before returning to TorrentToMedia and unpausing.
    ## Hopefully we can use a "getHistory" check in here to confirm processing complete...
    start = datetime.datetime.now()  # set time for timeout
    while (datetime.datetime.now() - start) < datetime.timedelta(minutes=1):  # only wait 2 minutes, then return to TorrentToMedia
        time.sleep(20) # Just stop this looping infinitely and hogging resources for 2 minutes ;)
    else:  # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resume seeding now.
        Logger.info("This album should have completed processing. Please check HeadPhones Logs")
        # Logger.warning("The album does not appear to have changed status after 2 minutes. Please check HeadPhones Logs")
    # return 1 # failure
    return 0 # success for now.
