import sys
import urllib
import os
import shutil
import ConfigParser
import datetime
import time
import json
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

def get_imdb(nzbName, dirName):
    
    a=nzbName.find('.cp(')+4 #search for .cptt( in nzbName
    b=nzbName[a:].find(')')+a
    imdbid=nzbName[a:b]
    
    if imdbid:
        Logger.info("Found movie id %s in name", imdbid) 
        return imdbid
    
    a=dirName.find('.cp(')+4 #search for .cptt( in dirname
    b=dirName[a:].find(')')+a
    imdbid=dirName[a:b]
    
    if imdbid:
        Logger.info("Found movie id %s in directory", imdbid) 
        return imdbid
    else:
        Logger.warning("Could not find an imdb id in directory or name")
        Logger.info("Postprocessing will continue, but the movie may not be identified correctly by CouchPotato")
        return ""

def get_movie_info(myOpener, baseURL, imdbid):
    
    if not imdbid:
        return ""
    url = baseURL + "movie.list"

    Logger.debug("Opening URL: %s", url)

    try:
        urlObj = myOpener.openit(url)
    except IOError, e:
        Logger.error("Unable to open URL: %s", str(e))
        return ""

    movie_id = ""
    result = json.load(urlObj)
    movieid = [item["id"] for item in result["movies"]]
    library = [item["library"]["identifier"] for item in result["movies"]]
    for index in range(len(movieid)):
        if library[index] == imdbid:
            movie_id = str(movieid[index])
            Logger.info("Found movie id %s in CPS database for movie %s", movie_id, imdbid)
            break
    return movie_id

def get_status(myOpener, baseURL, movie_id):
    
    if not movie_id:
        return ""
    url = baseURL + "movie.get/?id=" + str(movie_id)

    Logger.debug("Opening URL: %s", url)

    try:
        urlObj = myOpener.openit(url)
    except IOError, e:
        Logger.error("Unable to open URL: %s", str(e))
        return ""
    result = json.load(urlObj)
    try:
        movie_status = result["movie"]["status"]["identifier"]
        Logger.debug("This movie is marked as status %s in CouchPotatoServer", movie_status)
        return movie_status
    except e: # index out of range/doesn't exist?
        Logger.error("Could not find a status for this movie due to: %s", str(e))
        return ""

def process(dirName, nzbName=None, status=0):

    status = int(status)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

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
        
    try:    
        transcode = int(config.get("Transcoder", "transcode"))
    except (ConfigParser.NoOptionError, ValueError):
        transcode = 0

    myOpener = AuthURLOpener(username, password)

    nzbName = str(nzbName) # make sure it is a string
    
    imdbid = get_imdb(nzbName, dirName)

    if ssl:
        protocol = "https://"
    else:
        protocol = "http://"
    # don't delay when we are calling this script manually.
    if nzbName == "Manual Run":
        delay = 0

    baseURL = protocol + host + ":" + port + web_root + "/api/" + apikey + "/"
    
    movie_id = get_movie_info(myOpener, baseURL, imdbid) # get the CPS database movie id this movie.
    
    initial_status = get_status(myOpener, baseURL, movie_id)
    
    process_all_exceptions(nzbName.lower(), dirName)

    if status == 0:
        if transcode == 1:
            result = Transcoder.Transcode_file(dirName)
            if result == 0:
                Logger.debug("Transcoding succeeded for files in %s", dirName)
            else:
                Logger.warning("Transcoding failed for files in %s", dirName)

        if method == "manage":
            command = "manage.update"
        else:
            command = "renamer.scan"

        url = baseURL + command

        Logger.info("Waiting for %s seconds to allow CPS to process newly extracted files", str(delay))

        time.sleep(delay)

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            Logger.error("Unable to open URL: %s", str(e))
            return 1 # failure

        result = json.load(urlObj)
        Logger.info("CouchPotatoServer returned %s", result)
        if result['success']:
            Logger.info("%s started on CouchPotatoServer for %s", command, nzbName)
        else:
            Logger.error("%s has NOT started on CouchPotatoServer for %s. Exiting", command, nzbName)
            return 1 # failure

    else:
        Logger.info("Download of %s has failed.", nzbName)
        Logger.info("Trying to re-cue the next highest ranked release")
        
        if not movie_id:
            Logger.warning("Cound not find a movie in the database for release %s", nzbName)
            Logger.warning("Please manually ignore this release and refresh the wanted movie")
            Logger.error("Exiting autoProcessMovie script")
            return 1 # failure

        url = baseURL + "searcher.try_next/?id=" + movie_id

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = myOpener.openit(url)
        except IOError, e:
            Logger.error("Unable to open URL: %s", str(e))
            return 1 # failure

        result = urlObj.readlines()
        for line in result:
            Logger.info("%s", line)

        Logger.info("Movie %s set to try the next best release on CouchPotatoServer", movie_id)
        if delete_failed:
            Logger.info("Deleting failed files and folder %s", dirName)
            try:
                shutil.rmtree(dirName)
            except e:
                Logger.error("Unable to delete folder %s due to: %s", dirName, str(e))
        return 0 # success
    
    if nzbName == "Manual Run":
        return 0 # success

    # we will now check to see if CPS has finished renaming before returning to TorrentToMedia and unpausing.
    start = datetime.datetime.now()  # set time for timeout
    while (datetime.datetime.now() - start) < datetime.timedelta(minutes=2):  # only wait 2 minutes, then return to TorrentToMedia
        movie_status = get_status(myOpener, baseURL, movie_id) # get the current status fo this movie.
        if movie_status != initial_status:  # Something has changed. CPS must have processed this movie.
            Logger.info("SUCCESS: This movie is now marked as status %s in CouchPotatoServer", movie_status)
            return 0 # success
        time.sleep(20) # Just stop this looping infinitely and hogging resources for 2 minutes ;)
    else:  # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resule seeding now.
        Logger.warning("The movie does not appear to have changed status after 2 minutes. Please check CouchPotato Logs")
    return 1 # failure
