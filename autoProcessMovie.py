import sys
import urllib
import os
import shutil
import ConfigParser
import time
import json 
import logging

from nzbToMediaEnv import *

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

def custom_groups(group, dirName):
    mediaContainer = ['.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv', '.mp4', '.mpg', '.mpeg', '.iso']
    if group == "[=-< Q o Q >-=]": # for my NL friends :) we want to reverse the file names for the video files.
        for dirpath, dirnames, filenames in os.walk(dirName):
            for file in filenames:
                filePath = os.path.join(dirpath, file)
                fileExtention = os.path.splitext(file)[1]
                if fileExtention in mediaContainer:  # If the file is a video file
                    Logger.debug("Reversing the file name for a QoQ release %s", file)
                    newname = os.path.splitext(file)[0][::-1]
                    newfile = newname + fileExtention
                    newfilePath = os.path.join(dirpath, newfile)
                    os.rename(filePath, newfilePath)
                    Logger.debug("New file name is %s", newfile)
    else: # we can add more customizations here.
        pass

def process(dirName, nzbName=None, status=0):

    status = int(status)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)
    
    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        sys.exit(-1)
    
    config.read(configFilename)
    
    host = config.get("CouchPotato", "host")
    port = config.get("CouchPotato", "port")
    username = config.get("CouchPotato", "username")
    password = config.get("CouchPotato", "password")
    apikey = config.get("CouchPotato", "apikey")
    delay = float(config.get("CouchPotato", "delay"))
    method = config.get("CouchPotato", "method")
    delete_failed = int(config.get("CouchPotato", "delete_failed"))

    try:
        ssl = int(config.get("CouchPotato", "ssl"))
    except (ConfigParser.NoOptionError, ValueError):
        ssl = 0
   
    try:
        web_root = config.get("CouchPotato", "web_root")
    except ConfigParser.NoOptionError:
        web_root = ""

    myOpener = AuthURLOpener(username, password)

    nzbName1 = str(nzbName)

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    # don't delay when we are calling this script manually.    
    if  nzbName == "Manual Run":  
        delay = 0

    # check for custom groups
    customgroups = ['[=-< Q o Q >-=]']  # we can add more to this list
    for index in range(len(customgroups)):
        if customgroups[index].lower() in nzbName.lower(): # match the group in the nzbname
            custom_groups(customgroups[index], dirName) # files have been renamned
            break
        
    if status == 0:
        if method == "manage":
            command = "manage.update" 
        else:
            command = "renamer.scan" 

        url = protocol + host + ":" + port + web_root + "/api/" + apikey + "/" + command

        Logger.info("waiting for %s seconds to allow CPS to process newly extracted files", str(delay))

        time.sleep(delay)

        Logger.debug("Opening URL: %s", url)
    
        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            Logger.error("Unable to open URL: %s", str(e))
            sys.exit(1)
    
        result = json.load(urlObj)
        Logger.info("CouchPotatoServer returned %s", result)
        if result['success']:
            Logger.info("%s started on CouchPotatoServer for %s", command, nzbName1)
        else:
            Logger.error("%s has NOT started on CouchPotatoServer for %s", command, nzbName1)

    else:
        Logger.info("download of %s has failed.", nzbName1)
        Logger.info("trying to re-cue the next highest ranked release")
        a=nzbName1.find('.cp(')+4
        b=nzbName1[a:].find(')')+a
        imdbid=nzbName1[a:b]

        url = protocol + host + ":" + port + web_root + "/api/" + apikey + "/movie.list"
        
        Logger.debug("Opening URL: %s", url)
    
        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            Logger.error("Unable to open URL: %s", str(e))
            sys.exit(1)

        n=0
        result = json.load(urlObj)
        movieid = [item["id"] for item in result["movies"]]
        library = [item["library"] for item in result["movies"]]
        identifier = [item["identifier"] for item in library]
        for index in range(len(movieid)):
            if identifier[index] == imdbid:
                movid = str(movieid[index])
                Logger.info("found movie id %s in database for release %s", movid, nzbName1)
                n = n + 1
                break

        if n == 0:
            Logger.warning("cound not find a movie in the database for release %s", nzbName1)
            Logger.warning("please manually ignore this release and refresh the wanted movie")
            Logger.error("exiting postprocessing script")
            sys.exit(1)
        
        url = protocol + host + ":" + port + web_root + "/api/" + apikey + "/searcher.try_next/?id=" + movid
        
        Logger.debug("Opening URL: %s", url)
    
        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            Logger.error("Unable to open URL: %s", str(e))
            sys.exit(1)
        
        result = urlObj.readlines()
        for line in result:
            Logger.info("%s", line)
    
        Logger.info("movie %s set to try the next best release on CouchPotatoServer", movid)
        if delete_failed:
            Logger.info("Deleting failed files and folder %s", dirName)
            shutil.rmtree(dirName)
