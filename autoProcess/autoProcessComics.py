import sys
import urllib
import os.path
import time
import ConfigParser
import logging

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


def processEpisode(dirName, nzbName=None, status=0):

    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)
    
    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure
    
    config.read(configFilename)
  
    host = config.get("Mylar", "host")
    port = config.get("Mylar", "port")
    username = config.get("Mylar", "username")
    password = config.get("Mylar", "password")
    try:
        ssl = int(config.get("Mylar", "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0
    
    try:
        web_root = config.get("Mylar", "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    try:
        watch_dir = config.get("Mylar", "watch_dir")
    except ConfigParser.NoOptionError:
        watch_dir = ""
    params = {}

    if dirName == "Manual Run" and watch_dir != "":
        dirName = watch_dir
    
    params['nzb_folder'] = dirName
    if nzbName != None and nzbName != "Manual Run":
        params['nzb_name'] = nzbName
        
    myOpener = AuthURLOpener(username, password)
    
    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"

    url = protocol + host + ":" + port + web_root + "/post_process?" + urllib.urlencode(params)
    
    Logger.debug("Opening URL: %s", url)
    
    try:
        urlObj = myOpener.openit(url)
    except:
        Logger.exception("Unable to open URL")
        return 1 # failure
    
    result = urlObj.readlines()
    for line in result:
         Logger.info("%s", line)
    
    time.sleep(60) #wait 1 minute for now... need to see just what gets logged and how long it takes to process
    return 0 # Success        
