import urllib
import nzbtomedia
import requests
from nzbtomedia import logger

def autoFork(inputCategory):
    # auto-detect correct section
    section = nzbtomedia.CFG.findsection(inputCategory)
    if not section:
        logger.error(
            "We were unable to find a section for category %s, please check your autoProcessMedia.cfg file." % inputCategory)
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
    except:
        ssl = 0

    try:
        web_root = nzbtomedia.CFG[section][inputCategory]["web_root"]
    except:
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
        logger.info("Attempting to auto-detect %s fork" % inputCategory)
        for fork in sorted(nzbtomedia.FORKS.iteritems(), reverse=False):
            url = "%s%s:%s%s/home/postprocess/processEpisode?%s" % (protocol,host,port,web_root,urllib.urlencode(fork[1]))

            # attempting to auto-detect fork
            try:
                if username and password:
                    r = requests.get(url, auth=(username, password), verify=False)
                else:
                    r = requests.get(url, verify=False)
            except requests.ConnectionError:
                logger.info("Could not connect to %s:%s to perform auto-fork detection!" % (section, inputCategory))
                break

            if r.ok:
                detected = True
                break

        if detected:
            logger.info("%s:%s fork auto-detection successful ..." % (section, inputCategory))
        else:
            logger.info("%s:%s fork auto-detection failed" % (section, inputCategory))
            fork = nzbtomedia.FORKS.items()[nzbtomedia.FORKS.keys().index(nzbtomedia.FORK_DEFAULT)]

    logger.info("%s:%s fork set to %s" % (section, inputCategory, fork[0]))
    return fork[0], fork[1]