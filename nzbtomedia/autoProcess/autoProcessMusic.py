import time
import datetime
import logging
import socket
import urllib
from lib import requests
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, getDirectorySize

Logger = logging.getLogger()

class autoProcessMusic:
    def process(self, dirName, nzbName=None, status=0, clientAgent="manual", inputCategory=None):
        if dirName is None:
            Logger.error("No directory was given!")
            return 1  # failure

        # auto-detect correct section
        section = config().issubsection(inputCategory,checkenabled=True)[0]
        if len(section) == 0:
            Logger.error(
                "MAIN: We were unable to find a processor for category %s that was enabled, please check your autoProcessMedia.cfg file.", inputCategory)
            return 1

        socket.setdefaulttimeout(int(config.NZBTOMEDIA_TIMEOUT)) #initialize socket timeout.

        Logger.info("Loading config from %s", config.CONFIG_FILE)

        status = int(status)

        host = config()[section][inputCategory]["host"]
        port = config()[section][inputCategory]["port"]
        apikey = config()[section][inputCategory]["apikey"]
        delay = float(config()[section][inputCategory]["delay"])

        try:
            ssl = int(config()[section][inputCategory]["ssl"])
        except:
            ssl = 0
        try:
            web_root = config()[section][inputCategory]["web_root"]
        except:
            web_root = ""
        try:
            TimePerGiB = int(config()[section][inputCategory]["TimePerGiB"])
        except:
            TimePerGiB = 60 # note, if using Network to transfer on 100Mbit LAN, expect ~ 600 MB/minute.

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"
        # don't delay when we are calling this script manually.
        if clientAgent == "manual":
            delay = 0

        nzbName, dirName = convert_to_ascii(nzbName, dirName)

        dirSize = getDirectorySize(dirName) # get total directory size to calculate needed processing time.
        TIME_OUT = int(TimePerGiB) * dirSize # HeadPhones needs to complete all moving/transcoding and renaming before returning the status.
        TIME_OUT += 60 # Add an extra minute for over-head/processing/metadata.
        socket.setdefaulttimeout(int(TIME_OUT)) #initialize socket timeout.

        baseURL = protocol + host + ":" + port + web_root + "/api?"

        if status == 0:

            params = {}
            params['apikey'] = apikey
            params['cmd'] = "forceProcess"
            params['dir'] = dirName

            url = baseURL + + urllib.urlencode(params)

            Logger.info("Waiting for %s seconds to allow HeadPhones to process newly extracted files", str(delay))

            time.sleep(delay)

            Logger.debug("Opening URL: %s", url)

            try:
                r = requests.get(url)
            except requests.ConnectionError:
                Logger.exception("Unable to open URL")
                return 1  # failure

            Logger.info("HeadPhones returned %s", r.text)
            if r.text == "OK":
                Logger.info("Post-processing started on HeadPhones for %s in folder %s", nzbName, dirName)
            else:
                Logger.error("Post-proecssing has NOT started on HeadPhones for %s in folder %s. Exiting", nzbName, dirName)
                return 1 # failure

        else:
            Logger.info("The download failed. Nothing to process")
            return 0 # Success (as far as this script is concerned)

        if clientAgent == "manual":
            return 0 # success

        # we will now wait 1 minutes for this album to be processed before returning to TorrentToMedia and unpausing.
        ## Hopefully we can use a "getHistory" check in here to confirm processing complete...
        start = datetime.datetime.now()  # set time for timeout
        while (datetime.datetime.now() - start) < datetime.timedelta(minutes=1):  # only wait 2 minutes, then return to TorrentToMedia
            time.sleep(20) # Just stop this looping infinitely and hogging resources for 2 minutes ;)
        else:  # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resume seeding now.
            Logger.info("This album should have completed processing. Please check HeadPhones Logs")
            # Logger.warning("The album does not appear to have changed status after 2 minutes. Please check HeadPhones Logs")
        # return 1 # failure
        return 0 # success for now.
