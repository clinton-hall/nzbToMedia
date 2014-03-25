import sys
import urllib
import os
import ConfigParser
import logging

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

def autoFork(fork=None):
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    config.read(configFilename)

    # config settings
    section = "SickBeard"
    host = config.get(section, "host")
    port = config.get(section, "port")
    username = config.get(section, "username")
    password = config.get(section, "password")

    try:
        ssl = int(config.get(section, "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config.get(section, "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    try:
        fork = config.get(section, "fork")
    except ConfigParser.NoOptionError:
        fork = "auto"

    if fork in "auto":
        myOpener = AuthURLOpener(username, password)

        if ssl:
            protocol = "https://"
        else:
            protocol = "http://"

        Logger.info("Attempting to auto-detect SickBeard fork")
        for f in forks.iteritems():
            url = protocol + host + ":" + port + web_root + "/home/postprocess/processEpisode?" + urllib.urlencode(f[1]['params'])

            # attempting to auto-detect fork
            urlObj = myOpener.openit(url)

            if urlObj.getcode() == 200:
                Logger.info("SickBeard fork auto-detection successful. Fork set to %s", f[1]['name'])
                return f[1]['name'], f[1]['params']

        # failed to auto-detect fork
        Logger.info("SickBeard fork auto-detection failed")

    else: #if not fork in "auto"
        try:
            fork = fork if fork in SICKBEARD_FAILED or fork in SICKBEARD_TORRENT else fork_default
            fork = [f for f in forks.iteritems() if f[1]['name'] == fork][0]
        except:
            fork = [f for f in forks.iteritems() if f[1]['name'] == fork_default][0]

    Logger.info("SickBeard fork set to %s", fork[1]['name'])
    return fork[1]['name'], fork[1]['params']