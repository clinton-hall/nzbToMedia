import urllib
import time
import nzbtomedia
from lib import requests
from nzbtomedia.nzbToMediaUtil import convert_to_ascii
from nzbtomedia import logger

class autoProcessComics:
    def processEpisode(self, dirName, nzbName=None, status=0, clientAgent='manual', inputCategory=None):
        if dirName is None:
            logger.error("No directory was given!")
            return 1  # failure

        # auto-detect correct section
        section = nzbtomedia.CFG.findsection(inputCategory)
        if not section:
            logger.error(
                "We were unable to find a section for category %s, please check your autoProcessMedia.cfg file.", inputCategory)
            return 1

        host = nzbtomedia.CFG[section][inputCategory]["host"]
        port = nzbtomedia.CFG[section][inputCategory]["port"]
        username = nzbtomedia.CFG[section][inputCategory]["username"]
        password = nzbtomedia.CFG[section][inputCategory]["password"]

        try:
            ssl = int(nzbtomedia.CFG[section][inputCategory]["ssl"])
        except:
            ssl = 0

        try:
            web_root = nzbtomedia.CFG[section][inputCategory]["web_root"]
        except:
            web_root = ""

        try:
            watch_dir = nzbtomedia.CFG[section][inputCategory]["watch_dir"]
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

        logger.debug("Opening URL: %s", url)

        try:
            r = requests.get(url, auth=(username, password), stream=True)
        except requests.ConnectionError:
            logger.error("Unable to open URL")
            return 1 # failure

        for line in r.iter_lines():
            if line: logger.postprocess("%s", line)

        time.sleep(60) #wait 1 minute for now... need to see just what gets logged and how long it takes to process
        return 0 # Success
