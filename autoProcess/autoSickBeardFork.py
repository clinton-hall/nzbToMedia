import urllib
import logging

from nzbToMediaConfig import *
from autoProcess.nzbToMediaEnv import *

Logger = logging.getLogger()

class AuthURLOpener(urllib.FancyURLopener):
    def __init__(self, user, pw):
        self.username = user
        self.password = pw
        self.numTries = 0
        urllib.FancyURLopener.__init__(self)

    def prompt_user_passwd(self, host, realm):
        if self.numTries == 0:
            self.numTries = 1
            return (self.username, self.password)
        else:
            return ('', '')

    def openit(self, url):
        self.numTries = 0
        return urllib.FancyURLopener.open(self, url)

def autoFork():

    # config settings
    section = "SickBeard"
    host = config().get(section, "host")
    port = config().get(section, "port")
    username = config().get(section, "username")
    password = config().get(section, "password")

    try:
        ssl = int(config().get(section, "ssl"))
    except (config.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config().get(section, "web_root")
    except config.NoOptionError:
        web_root = ""

    try:
        fork = forks.items()[forks.keys().index(config().get(section, "fork"))]
    except:
        fork = "auto"

    myOpener = AuthURLOpener(username, password)

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    detected = False
    if fork == "auto":
        Logger.info("Attempting to auto-detect SickBeard fork")
        for fork in sorted(forks.iteritems()):
            url = protocol + host + ":" + port + web_root + "/home/postprocess/processEpisode?" + urllib.urlencode(fork[1])

            # attempting to auto-detect fork
            try:
                urlObj = myOpener.openit(url)
            except IOError, e:
                Logger.info("Could not connect to SickBeard to perform auto-fork detection!")
                break

            if urlObj.getcode() == 200:
                detected = True
                break

        if detected:
            Logger.info("SickBeard fork auto-detection successful ...")
        else:
            Logger.info("SickBeard fork auto-detection failed")
            fork = forks.items()[forks.keys().index(fork_default)]

    Logger.info("SickBeard fork set to %s", fork[0])
    return fork[0], fork[1]