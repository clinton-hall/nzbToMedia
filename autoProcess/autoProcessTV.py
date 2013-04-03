# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.


import sys
import urllib
import os
import ConfigParser
import logging

import Transcoder
from nzbToMediaEnv import *
from nzbToMediaSceneExceptions import process_all_exceptions

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


def processEpisode(dirName, nzbName=None, failed=False):

    status = int(failed)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    try:
        fp = open(configFilename, "r")
        config.readfp(fp)
        fp.close()
    except IOError, e:
        Logger.error("Could not read configuration file: %s", str(e))
        return 1 # failure

    watch_dir = ""
    host = config.get("SickBeard", "host")
    port = config.get("SickBeard", "port")
    username = config.get("SickBeard", "username")
    password = config.get("SickBeard", "password")
    try:
        ssl = int(config.get("SickBeard", "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0

    try:
        web_root = config.get("SickBeard", "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    try:
        watch_dir = config.get("SickBeard", "watch_dir")
    except ConfigParser.NoOptionError:
        watch_dir = ""

    try:
        failed_fork = int(config.get("SickBeard", "failed_fork"))
    except (ConfigParser.NoOptionError, ValueError):
        failed_fork = 0
    try:    
        transcode = int(config.get("Transcoder", "transcode"))
    except (ConfigParser.NoOptionError, ValueError):
        transcode = 0

    process_all_exceptions(nzbName.lower(), dirName)


    #allows manual call of postprocess script if we have specified a watch_dir. Check that here.
    if nzbName == "Manual Run" and watch_dir == "":
        Logger.error("In order to run this script manually you must specify a watch_dir in autoProcessTV.cfg")
        return 1 # failure
    #allows us to specify the default watch directory and call the postproecssing on another PC with different directory structure.
    if watch_dir != "":
        dirName = watch_dir

    params = {}

    params['quiet'] = 1

    # if you have specified you are using development branch from fork https://github.com/Tolstyak/Sick-Beard.git
    if failed_fork:
        params['dirName'] = dirName
        if nzbName != None:
            params['nzbName'] = nzbName
        params['failed'] = failed
        if status == 0:
            Logger.info("The download succeeded. Sending process request to SickBeard's failed branch")
        else:
            Logger.info("The download failed. Sending 'failed' process request to SickBeard's failed branch")
            

    # this is our default behaviour to work with the standard Master branch of SickBeard
    else:
        params['dir'] = dirName
        if nzbName != None:
            params['nzbName'] = nzbName
        # the standard Master bamch of SickBeard cannot process failed downloads. So Exit here.
        if status == 0:
            Logger.info("The download succeeded. Sending process request to SickBeard")
        else:
            Logger.info("The download failed. Nothing to process")
            return 0 # Success (as far as this script is concerned)
    
    if status == 0 and transcode == 1: # only transcode successful downlaods
        result = Transcoder.Transcode_directory(dirName)
        if result == 0:
            Logger.debug("Transcoding succeeded for files in %s", dirName)
        else:
            Logger.warning("Transcoding failed for files in %s", dirName)

    myOpener = AuthURLOpener(username, password)

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + host + ":" + port + web_root + "/home/postprocess/processEpisode?" + urllib.urlencode(params)

    Logger.debug("Opening URL: %s", url)

    try:
        urlObj = myOpener.openit(url)
    except IOError, e:
        Logger.error("Unable to open URL: %s", str(e))
        return 1 # failure

    result = urlObj.readlines()
    for line in result:
        Logger.info("%s", line.rstrip())
    return 0 # Success
