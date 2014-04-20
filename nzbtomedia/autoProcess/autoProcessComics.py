import os
import time
import nzbtomedia
from lib import requests
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, joinPath
from nzbtomedia import logger

class autoProcessComics:
    def processEpisode(self, dirName, nzbName=None, status=0, clientAgent='manual', inputCategory=None):
        # auto-detect correct section
        section = nzbtomedia.CFG.findsection(inputCategory)
        if not section:
            logger.error(
                "We were unable to find a section for category %s, please check your autoProcessMedia.cfg file." % inputCategory)
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
            remote_path = nzbtomedia.CFG[section][inputCategory]["remote_path"]
        except:
            remote_path = None

        nzbName, dirName = convert_to_ascii(nzbName, dirName)

        params = {}
        params['nzb_folder'] = dirName
        if remote_path:
            dirName_new = joinPath(remote_path, os.path.basename(dirName)).replace("\\", "/")
            params['nzb_folder'] = dirName_new

        if nzbName != None:
            params['nzb_name'] = nzbName

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        url = "%s%s:%s%s/post_process" % (protocol, host, port, web_root)
        logger.debug("Opening URL: %s" % (url), section)

        try:
            r = requests.get(url, params=params, auth=(username, password), stream=True)
        except requests.ConnectionError:
            logger.error("Unable to open URL", section)
            return 1 # failure

        for line in r.iter_lines():
            if line: logger.postprocess("%s" % (line), section)

        time.sleep(60) #wait 1 minute for now... need to see just what gets logged and how long it takes to process
        return 0 # Success
