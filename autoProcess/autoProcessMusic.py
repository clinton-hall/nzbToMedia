import sys
import urllib
import os
import shutil
import ConfigParser
import datetime
import time
import json
import logging

from nzbToMediaEnv import *

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

def process(dirName, nzbName=None, status=0):

    status = int(status)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    config.read(configFilename)

    host = config.get("HeadPhones", "host")
    port = config.get("HeadPhones", "port")
    username = config.get("HeadPhones", "username")
    password = config.get("HeadPhones", "password")
    apikey = config.get("HeadPhones", "apikey")
    delay = float(config.get("HeadPhones", "delay"))

    try:
        ssl = int(config.get("HeadPhones", "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config.get("HeadPhones", "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    myOpener = AuthURLOpener(username, password)

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    # don't delay when we are calling this script manually.
    if nzbName == "Manual Run":
        delay = 0

    baseURL = protocol + host + ":" + port + web_root + "/api?apikey=" + apikey + "&cmd="

    if status == 0:
        command = "forceProcess"

        url = baseURL + command

        Logger.info("Waiting for %s seconds to allow HeadPhones to process newly extracted files", str(delay))

        time.sleep(delay)

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            Logger.error("Unable to open URL: %s", str(e))
            return 1 # failure

        result = urlObj.readlines()
        Logger.info("HeaPhones returned %s", result)
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
