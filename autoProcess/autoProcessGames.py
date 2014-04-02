import urllib
import json
import logging

from nzbToMediaEnv import *
from nzbToMediaUtil import *


Logger = logging.getLogger()
socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

def process(dirName, nzbName=None, status=0, inputCategory=None):

    status = int(status)


    Logger.info("Loading config from %s", CONFIG_FILE)

    if not config():
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure



    section = "Gamez"
    if inputCategory != None and config().has_section(inputCategory):
        section = inputCategory

    host = config().get(section, "host")
    port = config().get(section, "port")
    apikey = config().get(section, "apikey")

    try:
        ssl = int(config().get(section, "ssl"))
    except (config.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config().get(section, "web_root")
    except config.NoOptionError:
        web_root = ""

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    nzbName, dirName = converto_to_ascii(nzbName, dirName)

    baseURL = protocol + host + ":" + port + web_root + "/api?api_key=" + apikey + "&mode="

    fields = nzbName.split("-")
    gamezID = fields[0].replace("[","").replace("]","").replace(" ","")
    downloadStatus = 'Wanted'
    if status == 0:
        downloadStatus = 'Downloaded'

    url = baseURL + "UPDATEREQUESTEDSTATUS&db_id=" + gamezID + "&status=" + downloadStatus

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
