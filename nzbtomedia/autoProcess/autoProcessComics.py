import os
import time
import nzbtomedia
import requests
from nzbtomedia.nzbToMediaUtil import convert_to_ascii
from nzbtomedia import logger

class autoProcessComics:
    def processEpisode(self, section, dirName, inputName=None, status=0, clientAgent='manual', inputCategory=None):
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

        inputName, dirName = convert_to_ascii(inputName, dirName)

        params = {}
        params['nzb_folder'] = dirName
        if remote_path:
            params['nzb_folder'] = os.path.join(remote_path, os.path.basename(dirName))

        if inputName != None:
            params['nzb_name'] = inputName

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        url = "%s%s:%s%s/post_process" % (protocol, host, port, web_root)
        logger.debug("Opening URL: %s" % (url), section)

        try:
            r = requests.get(url, params=params, auth=(username, password), stream=True, verify=False)
        except requests.ConnectionError:
            logger.error("Unable to open URL", section)
            return 1 # failure

        for line in r.iter_lines():
            if line: logger.postprocess("%s" % (line), section)

        time.sleep(60) #wait 1 minute for now... need to see just what gets logged and how long it takes to process
        return 0 # Success
