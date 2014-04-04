import logging
import urllib
import requests
import socket
import time
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaUtil import convert_to_ascii

Logger = logging.getLogger()

class autoProcessComics:
    def processEpisode(self, dirName, nzbName=None, status=0, clientAgent='manual', inputCategory=None):
        if dirName is None:
            Logger.error("No directory was given!")
            return 1  # failure

        socket.setdefaulttimeout(int(config.NZBTOMEDIA_TIMEOUT)) #initialize socket timeout.

        Logger.info("Loading config from %s", config.CONFIG_FILE)

        section = "Mylar"
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
