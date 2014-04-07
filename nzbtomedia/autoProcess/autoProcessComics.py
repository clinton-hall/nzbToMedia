import logging
import urllib
import socket
import time
from lib import requests
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaUtil import convert_to_ascii

Logger = logging.getLogger()

class autoProcessComics:
    def processEpisode(self, dirName, nzbName=None, status=0, clientAgent='manual', inputCategory=None):
        if dirName is None:
            Logger.error("No directory was given!")
            return 1  # failure

        # auto-detect correct section
        section = config.issubsection(inputCategory, checkenabled=True)[0]
        if not section:
            Logger.error(
                "MAIN: We were unable to find a processor for category %s that was enabled, please check your autoProcessMedia.cfg file.", inputCategory)
            return 1

        socket.setdefaulttimeout(int(config.NZBTOMEDIA_TIMEOUT)) #initialize socket timeout.

        Logger.info("Loading config from %s", config.CONFIG_FILE)


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
        params = {}

        nzbName, dirName = convert_to_ascii(nzbName, dirName)

        if dirName == "Manual Run" and watch_dir != "":
            dirName = watch_dir

        params['nzb_folder'] = dirName
        if nzbName != None:
            params['nzb_name'] = nzbName

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        url = protocol + host + ":" + port + web_root + "/post_process?" + urllib.urlencode(params)

        Logger.debug("Opening URL: %s", url)

        try:
            r = requests.get(url, auth=(username, password), stream=True)
        except requests.ConnectionError:
            Logger.exception("Unable to open URL")
            return 1 # failure

        for line in r.iter_lines():
            if line: Logger.info("%s", line)

        time.sleep(60) #wait 1 minute for now... need to see just what gets logged and how long it takes to process
        return 0 # Success
