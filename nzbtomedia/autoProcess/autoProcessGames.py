import nzbtomedia
import requests
import shutil
from nzbtomedia.nzbToMediaUtil import convert_to_ascii
from nzbtomedia.nzbToMediaSceneExceptions import process_all_exceptions
from nzbtomedia import logger

class autoProcessGames:
    def process(self, section, dirName, inputName=None, status=0, clientAgent='manual', inputCategory=None):
        status = int(status)

        host = nzbtomedia.CFG[section][inputCategory]["host"]
        port = nzbtomedia.CFG[section][inputCategory]["port"]
        apikey = nzbtomedia.CFG[section][inputCategory]["apikey"]
        try:
            library = nzbtomedia.CFG[section][inputCategory]["library"]
        except:
            library = None
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
        if library:
            logger.postprocess("moving files to library: %s" % (library),section)
            try:
                shutil.move(dirName, os.path.join(library, inputName))
            except:
                logger.error("Unable to move %s to %s" % (dirName, os.path.join(library, inputName)), section)
                return 1
        else:
            logger.error("No library specified to move files to. Please edit your configuration.", section)
            return 1

        if not r.status_code in [requests.codes.ok, requests.codes.created, requests.codes.accepted]:
            logger.error("Server returned status %s" % (str(r.status_code)), section)
            return 1
        elif result['success']:
            logger.postprocess("SUCCESS: Status for %s has been set to %s in Gamez" % (gamezID, downloadStatus),section)
            return 0 # Success
        else:
            logger.error("FAILED: Status for %s has NOT been updated in Gamez" % (gamezID),section)
            return 1 # failure
