import time
import datetime
import urllib
import nzbtomedia
from lib import requests
from nzbtomedia.nzbToMediaUtil import convert_to_ascii
from nzbtomedia import logger

class autoProcessMusic:
    def process(self, dirName, nzbName=None, status=0, clientAgent="manual", inputCategory=None):
        if dirName is None:
            logger.error("No directory was given!")
            return 1  # failure

        # auto-detect correct section
        section = nzbtomedia.CFG.findsection(inputCategory)
        if len(section) == 0:
            logger.error(
                "We were unable to find a section for category %s, please check your autoProcessMedia.cfg file.", inputCategory)
            return 1

        logger.postprocess("#########################################################")
        logger.postprocess("## ..::[%s]::.. :: CATEGORY:[%s]", section, inputCategory)
        logger.postprocess("#########################################################")

        status = int(status)

        host = nzbtomedia.CFG[section][inputCategory]["host"]
        port = nzbtomedia.CFG[section][inputCategory]["port"]
        apikey = nzbtomedia.CFG[section][inputCategory]["apikey"]
        delay = float(nzbtomedia.CFG[section][inputCategory]["delay"])

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
        # don't delay when we are calling this script manually.
        if clientAgent == "manual":
            delay = 0

        nzbName, dirName = convert_to_ascii(nzbName, dirName)

        baseURL = protocol + host + ":" + port + web_root + "/api?"

        if status == 0:

            params = {}
            params['apikey'] = apikey
            params['cmd'] = "forceProcess"
            params['dir'] = dirName

            url = baseURL

            logger.postprocess("Waiting for %s seconds to allow HeadPhones to process newly extracted files", str(delay))

            time.sleep(delay)

            logger.debug("Opening URL: %s", url)

            try:
                r = requests.get(url, data=params)
            except requests.ConnectionError:
                logger.error("Unable to open URL")
                return 1  # failure

            logger.postprocess("HeadPhones returned %s", r.text)
            if r.text == "OK":
                logger.postprocess("Post-processing started on HeadPhones for %s in folder %s", nzbName, dirName)
            else:
                logger.error("Post-proecssing has NOT started on HeadPhones for %s in folder %s. Exiting", nzbName, dirName)
                return 1 # failure

        else:
            logger.postprocess("The download failed. Nothing to process")
            return 0 # Success (as far as this script is concerned)

        if clientAgent == "manual":
            return 0 # success

        # we will now wait 1 minutes for this album to be processed before returning to TorrentToMedia and unpausing.
        ## Hopefully we can use a "getHistory" check in here to confirm processing complete...
        start = datetime.datetime.now()  # set time for timeout
        while (datetime.datetime.now() - start) < datetime.timedelta(minutes=1):  # only wait 2 minutes, then return to TorrentToMedia
            time.sleep(20) # Just stop this looping infinitely and hogging resources for 2 minutes ;)
        else:  # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resume seeding now.
            logger.postprocess("This album should have completed processing. Please check HeadPhones Logs")
            # logger.warning("The album does not appear to have changed status after 2 minutes. Please check HeadPhones Logs")
        # return 1 # failure
        return 0 # success for now.
