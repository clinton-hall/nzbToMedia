import logging
import urllib

import nzbtomedia

from lib import requests
from nzbToMediaConfig import config

def autoFork(inputCategory):

    Logger = logging.getLogger()

    # auto-detect correct section
    section = nzbtomedia.CFG.findsection(inputCategory)
    if not section:
        logger.error(
            "We were unable to find a section for category %s, please check your autoProcessMedia.cfg file.", inputCategory)
        return 1

    # config settings
    try:
        host = nzbtomedia.CFG[section][inputCategory]["host"]
        port = nzbtomedia.CFG[section][inputCategory]["port"]
    except:
        host = None
        port = None

    try:
        username = nzbtomedia.CFG[section][inputCategory]["username"]
        password = nzbtomedia.CFG[section][inputCategory]["password"]
    except:
        username = None
        password = None

    try:
        ssl = int(nzbtomedia.CFG[section][inputCategory]["ssl"])
    except (config, ValueError):
        ssl = 0

    try:
        web_root = nzbtomedia.CFG[section][inputCategory]["web_root"]
    except config:
        web_root = ""

    try:
        fork = nzbtomedia.FORKS.items()[nzbtomedia.FORKS.keys().index(nzbtomedia.CFG[section][inputCategory]["fork"])]
    except:
        fork = "auto"

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    detected = False
    if fork == "auto":
        logger.info("Attempting to auto-detect " + section + " fork")
        for fork in sorted(nzbtomedia.FORKS.iteritems()):
            url = protocol + host + ":" + port + web_root + "/home/postprocess/processEpisode?" + urllib.urlencode(fork[1])

            # attempting to auto-detect fork
            try:
                if username and password:
                    r = requests.get(url, auth=(username, password))
                else:
                    r = requests.get(url)
            except requests.ConnectionError:
                logger.info("Could not connect to " + section + ":" + inputCategory + " to perform auto-fork detection!")
                break

            if r.ok:
                detected = True
                break

        if detected:
            logger.info("" + section + ":" + inputCategory + " fork auto-detection successful ...")
        else:
            logger.info("" + section + ":" + inputCategory + " fork auto-detection failed")
            fork = nzbtomedia.FORKS.items()[nzbtomedia.FORKS.keys().index(nzbtomedia.FORK_DEFAULT)]

    logger.info("" + section + ":" + inputCategory + " fork set to %s", fork[0])
    return fork[0], fork[1]