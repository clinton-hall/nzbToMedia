import logging
import urllib
import requests

from nzbToMediaConfig import config

def autoFork(section):
    Logger = logging.getLogger()

    # config settings
    host = config().get(section, "host")
    port = config().get(section, "port")

    try:
        username = config().get(section, "username")
        password = config().get(section, "password")
    except:
        username = None
        password = None

    try:
        ssl = int(config().get(section, "ssl"))
    except (config.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config().get(section, "web_root")
    except config.NoOptionError:
        web_root = ""

    try:
        fork = config.FORKS.items()[config.FORKS.keys().index(config().get(section, "fork"))]
    except:
        fork = "auto"

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    detected = False
    if fork == "auto":
        Logger.info("Attempting to auto-detect SickBeard fork")
        for fork in sorted(config.FORKS.iteritems()):
            url = protocol + host + ":" + port + web_root + "/home/postprocess/processEpisode?" + urllib.urlencode(fork[1])

            # attempting to auto-detect fork
            try:
                if username and password:
                    r = requests.get(url, auth=(username, password))
                else:
                    r = requests.get(url)
            except requests.ConnectionError:
                Logger.info("Could not connect to SickBeard to perform auto-fork detection!")
                break

            if r.ok:
                detected = True
                break

        if detected:
            Logger.info("SickBeard fork auto-detection successful ...")
        else:
            Logger.info("SickBeard fork auto-detection failed")
            fork = config.FORKS.items()[config.FORKS.keys().index(config.FORK_DEFAULT)]

    Logger.info("SickBeard fork set to %s", fork[0])
    return fork[0], fork[1]