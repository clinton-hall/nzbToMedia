import json
import logging
import socket
from lib import requests
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaUtil import convert_to_ascii

Logger = logging.getLogger()

class autoProcessGames:
    def process(self, dirName, nzbName=None, status=0, clientAgent='manual', inputCategory=None):
        if dirName is None:
            Logger.error("No directory was given!")
            return 1  # failure

        # auto-detect correct section
        section = [x for x in config.issubsection(inputCategory) if config()[x][inputCategory]['enabled'] == 1]
        if len(section) > 1:
            Logger.error(
                "MAIN: You can't have multiple sub-sections with the same name enabled, fix your autoProcessMedia.cfg file.")
            return 1
        elif len(section) == 0:
            Logger.error(
                "MAIN: We were unable to find a processor for category %s that was enabled, please check your autoProcessMedia.cfg file.", inputCategory)
            return 1


        socket.setdefaulttimeout(int(config.NZBTOMEDIA_TIMEOUT)) #initialize socket timeout.

        Logger.info("Loading config from %s", config.CONFIG_FILE)

        status = int(status)

        host = config()[section][inputCategory]["host"]
        port = config()[section][inputCategory]["port"]
        apikey = config()[section][inputCategory]["apikey"]

        try:
            ssl = int(config()[section][inputCategory]["ssl"])
        except:
            ssl = 0

        try:
            web_root = config()[section][inputCategory]["web_root"]
        except:
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
            r = requests.get(url, stream=True)
        except requests.ConnectionError:
            Logger.exception("Unable to open URL")
            return 1  # failure

        result = {}
        for line in r.iter_lines():
            if line:
                Logger.info("%s", line)
                result.update(json.load(line))

        if result['success']:
            Logger.info("Status for %s has been set to %s in Gamez", gamezID, downloadStatus)
            return 0 # Success
        else:
            Logger.error("Status for %s has NOT been updated in Gamez", gamezID)
            return 1 # failure
