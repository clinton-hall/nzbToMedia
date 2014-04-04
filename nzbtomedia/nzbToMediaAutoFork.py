import logging
import urllib

from lib import requests

from nzbToMediaConfig import config

def autoFork(section, category):

    Logger = logging.getLogger()

    # config settings
    try:
        host = config()[section][category]["host"]
        port = config()[section][category]["port"]
    except:
        host = None
        port = None

    try:
        username = config()[section][category]["username"]
        password = config()[section][category]["password"]
    except:
        username = None
        password = None

    try:
        ssl = int(config()[section][category]["ssl"])
    except (config, ValueError):
        ssl = 0

    try:
        web_root = config()[section][category]["web_root"]
    except config:
        web_root = ""

    try:
        fork = config.FORKS.items()[config.FORKS.keys().index(config()[section][category]["fork"])]
    except:
        fork = "auto"

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    detected = False
    if fork == "auto":
        Logger.info("Attempting to auto-detect " + section + " fork")
        for fork in sorted(config.FORKS.iteritems()):
            url = protocol + host + ":" + port + web_root + "/home/postprocess/processEpisode?" + urllib.urlencode(fork[1])

            # attempting to auto-detect fork
            try:
                if username and password:
                    r = requests.get(url, auth=(username, password))
                else:
                    r = requests.get(url)
            except requests.ConnectionError:
                Logger.info("Could not connect to " + section + ":" + category + " to perform auto-fork detection!")
                break

            if r.ok:
                detected = True
                break

        if detected:
            Logger.info("" + section + ":" + category + " fork auto-detection successful ...")
        else:
            Logger.info("" + section + ":" + category + " fork auto-detection failed")
            fork = config.FORKS.items()[config.FORKS.keys().index(config.FORK_DEFAULT)]

    Logger.info("" + section + ":" + category + " fork set to %s", fork[0])
    return fork[0], fork[1]