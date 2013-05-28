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

def process(dirName, nzbName=None, status=0):

    status = int(status)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    config.read(configFilename)

    host = config.get("Gamez", "host")
    port = config.get("Gamez", "port")
    apikey = config.get("Gamez", "apikey")

    try:
        ssl = int(config.get("Gamez", "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config.get("Gamez", "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    baseURL = protocol + host + ":" + port + web_root + "/api?api_key=" + apikey + "&mode="

    fields = nzbName.split("-")
    gamezID = fields[0].replace("[","").replace("]","").replace(" ","")
    downloadStatus = 'Wanted'
    if status == 0:
        downloadStatus = 'Downloaded'

    URL = baseURL + "UPDATEREQUESTEDSTATUS&db_id=" + gamezID + "&status=" + downloadStatus

    Logger.debug("Opening URL: %s", url)

    try:
        urlObj = urllib.urlopen(url)
    except:
        Logger.exception("Unable to open URL")
        return 1 # failure

    result = json.load(urlObj)
    Logger.info("Gamez returned %s", result)
    if result['success']:
        Logger.info("Status for %s has been set to %s in Gamez", gamezID, downloadStatus)
        return 0 # Success
    else:
        Logger.error("Status for %s has NOT been updated in Gamez", gamezID)
        return 1 # failure
