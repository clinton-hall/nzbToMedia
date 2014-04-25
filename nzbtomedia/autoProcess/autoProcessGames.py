import nzbtomedia
import requests
from nzbtomedia.nzbToMediaUtil import convert_to_ascii
from nzbtomedia import logger

class autoProcessGames:
    def process(self, section, dirName, inputName=None, status=0, clientAgent='manual', inputCategory=None):
        status = int(status)

        host = nzbtomedia.CFG[section][inputCategory]["host"]
        port = nzbtomedia.CFG[section][inputCategory]["port"]
        apikey = nzbtomedia.CFG[section][inputCategory]["apikey"]

        try:
            ssl = int(nzbtomedia.CFG[section][inputCategory]["ssl"])
        except:
            ssl = 0

        try:
            web_root = nzbtomedia.CFG[section][inputCategory]["web_root"]
        except:
            web_root = ""

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        inputName, dirName = convert_to_ascii(inputName, dirName)

        url = "%s%s:%s%s/api" % (protocol, host, port, web_root)

        fields = inputName.split("-")

        gamezID = fields[0].replace("[","").replace("]","").replace(" ","")

        downloadStatus = 'Wanted'
        if status == 0:
            downloadStatus = 'Downloaded'

        params = {}
        params['api_key'] = apikey
        params['mode'] = 'UPDATEREQUESTEDSTATUS'
        params['db_id'] = gamezID
        params['status'] = downloadStatus

        logger.debug("Opening URL: %s" % (url),section)

        try:
            r = requests.get(url, params=params, verify=False)
        except requests.ConnectionError:
            logger.error("Unable to open URL")
            return 1  # failure

        result = r.json()
        logger.postprocess("%s" % (result),section)

        if result['success']:
            logger.postprocess("SUCCESS: Status for %s has been set to %s in Gamez" % (gamezID, downloadStatus),section)
            return 0 # Success
        else:
            logger.error("FAILED: Status for %s has NOT been updated in Gamez" % (gamezID),section)
            return 1 # failure
