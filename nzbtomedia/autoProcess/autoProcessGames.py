import json
import logging
import socket
import requests
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaUtil import convert_to_ascii

Logger = logging.getLogger()

class autoProcessGames:
    def process(self, dirName, nzbName=None, status=0, clientAgent='manual', inputCategory=None):
        if dirName is None:
            Logger.error("No directory was given!")
            return 1  # failure

        socket.setdefaulttimeout(int(config.NZBTOMEDIA_TIMEOUT)) #initialize socket timeout.

        Logger.info("Loading config from %s", config.CONFIG_FILE)

        status = int(status)

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

        nzbName, dirName = convert_to_ascii(nzbName, dirName)

        baseURL = protocol + host + ":" + port + web_root + "/api?api_key=" + apikey + "&mode="

        fields = nzbName.split("-")
        gamezID = fields[0].replace("[","").replace("]","").replace(" ","")
        downloadStatus = 'Wanted'
        if status == 0:
            downloadStatus = 'Downloaded'

        url = baseURL + "UPDATEREQUESTEDSTATUS&db_id=" + gamezID + "&status=" + downloadStatus

        Logger.debug("Opening URL: %s", url)

        try:
            r = requests.get(url)
        except requests.ConnectionError:
            Logger.exception("Unable to open URL")
            return 1  # failure

        result = json.load(r.text)
        Logger.info("Gamez returned %s", result)
        if result['success']:
            Logger.info("Status for %s has been set to %s in Gamez", gamezID, downloadStatus)
            return 0 # Success
        else:
            Logger.error("Status for %s has NOT been updated in Gamez", gamezID)
            return 1 # failure
