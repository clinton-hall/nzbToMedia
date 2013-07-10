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
 
    imdbid = ""    

    a = nzbName.find('.cp(') + 4 #search for .cptt( in nzbName
    b = nzbName[a:].find(')') + a
    if a > 3: # a == 3 if not exist
        imdbid = nzbName[a:b]
    
    if imdbid:
        Logger.info("Found movie id %s in name", imdbid) 
        return imdbid
    
    a = dirName.find('.cp(') + 4 #search for .cptt( in dirname
    b = dirName[a:].find(')') + a
    if a > 3: # a == 3 if not exist
        imdbid = dirName[a:b]
    
    if imdbid:
        Logger.info("Found movie id %s in directory", imdbid) 
        return imdbid

    else:
        Logger.warning("Could not find an imdb id in directory or name")
        Logger.info("Postprocessing will continue, but the movie may not be identified correctly by CouchPotato")
        return ""

def get_movie_info(myOpener, baseURL, imdbid, download_id):
    
    if not imdbid and not download_id:
        return ""
    url = baseURL + "movie.list/?status=active"

    Logger.debug("Opening URL: %s", url)

    try:
        urlObj = myOpener.openit(url)
    except:
        Logger.exception("Unable to open URL")
        return ""

    movie_id = ""
    try:
        result = json.load(urlObj)
        movieid = [item["id"] for item in result["movies"]]
        library = [item["library"]["identifier"] for item in result["movies"]]
        releases = [item["releases"] for item in result["movies"]]
        imdbid_list = []
        if not imdbid:
            movieindex = [index for index in range(len(movieid)) if len(releases[index]) > 0] 
            for index in movieindex:
                releaseindex = [index2 for index2 in range(len(releases[index])) if len(releases[index][index2]) > 0 and "download_id" in releases[index][index2]["info"] and releases[index][index2]["info"]["download_id"].lower() == download_id.lower()]
                if len(releaseindex) > 0:
                    imdbid_list.append(library[index])
            unique_imdbid_list = list(set(imdbid_list)) # convert this to a unique list to be sure we only have one imdbid
            if len(unique_imdbid_list) == 1: # we found it.
                imdbid = unique_imdbid_list[0]
                Logger.info("Found movie id %s in database via download_id %s", imdbid, download_id)
            else:
                return ""

        for index in range(len(movieid)):
            if library[index] == imdbid:
                movie_id = str(movieid[index])
                Logger.info("Found movie id %s in CPS database for movie %s", movie_id, imdbid)
                break
    except:
        if not imdbid:
            Logger.exception("Could not parse database results to determine imdbid or movie id")
        else:
            Logger.exception("Could not parse database results to determine movie id for imdbid: %s", imdbid)

    return movie_id

def get_status(myOpener, baseURL, movie_id, clientAgent, download_id):
    
    if not movie_id:
        return "", clientAgent, "none", "none"
    url = baseURL + "movie.get/?id=" + str(movie_id)
    Logger.debug("Looking for status of movie: %s - with release sent to clientAgent: %s and download_id: %s", movie_id, clientAgent, download_id)
    Logger.debug("Opening URL: %s", url)

    try:
        urlObj = myOpener.openit(url)
    except:
        Logger.exception("Unable to open URL")
        return "", clientAgent, "none", "none"
    result = json.load(urlObj)
    try:
        movie_status = result["movie"]["status"]["identifier"]
        Logger.debug("This movie is marked as status %s in CouchPotatoServer", movie_status)
    except: # index out of range/doesn't exist?
        Logger.exception("Could not find a status for this movie")
        movie_status = ""
    try:
        release_status = "none"
        if download_id != "" and download_id != "none": # we have the download id from the downloader. Let's see if it's valid.
            release_statuslist = [item["status"]["identifier"] for item in result["movie"]["releases"] if "download_id" in item["info"] and item["info"]["download_id"].lower() == download_id.lower()]
            clientAgentlist = [item["info"]["download_downloader"] for item in result["movie"]["releases"] if "download_id" in item["info"] and item["info"]["download_id"].lower() == download_id.lower()]
            if len(release_statuslist) == 1: # we have found a release by this id. :)
                release_status = release_statuslist[0]
                clientAgent = clientAgentlist[0]
                Logger.debug("Found a single release with download_id: %s for clientAgent: %s. Release status is: %s", download_id, clientAgent, release_status)
                return movie_status, clientAgent, download_id, release_status
            elif len(release_statuslist) > 1: # we have found many releases by this id. Check for snatched status
                clients = [item for item in clientAgentlist if item.lower() == clientAgent.lower()]
                clientAgent = clients[0]
                if len(clients) == 1: # ok.. a unique entry for download_id and clientAgent ;)
                    release_status = [item["status"]["identifier"] for item in result["movie"]["releases"] if "download_id" in item["info"] and item["info"]["download_id"].lower() == download_id.lower() and item["info"]["download_downloader"] == clientAgent][0]
                    Logger.debug("Found a single release for download_id: %s and clientAgent: %s. Release status is: %s", download_id, clientAgent, release_status)
                else: # doesn't matter. only really used as secondary confirmation of movie status change. Let's continue.                
                    Logger.debug("Found several releases for download_id: %s and clientAgent: %s. Cannot determine the release status", download_id, clientAgent)
                return movie_status, clientAgent, download_id, release_status
            else: # clearly the id we were passed doesn't match the database. Reset it and search all snatched releases.... hence the next if (not elif ;) )
                download_id = "" 
        if download_id == "none": # if we couldn't find this initially, there is no need to check next time around.
            return movie_status, clientAgent, download_id, release_status
        elif download_id == "": # in case we didn't get this from the downloader.
            download_idlist = [item["info"]["download_id"] for item in result["movie"]["releases"] if item["status"]["identifier"] == "snatched"]
            clientAgentlist = [item["info"]["download_downloader"] for item in result["movie"]["releases"] if item["status"]["identifier"] == "snatched"]
            if len(clientAgentlist) == 1:
                if clientAgent == "manual":
                    clientAgent = clientAgentlist[0]
                    download_id = download_idlist[0]
                    release_status = "snatched"
                elif clientAgent.lower() == clientAgentlist[0].lower():
                    download_id = download_idlist[0]
                    clientAgent = clientAgentlist[0]
                    release_status = "snatched"
                Logger.debug("Found a single download_id: %s and clientAgent: %s. Release status is: %s", download_id, clientAgent, release_status) 
            elif clientAgent == "manual":
                download_id = "none"
                release_status = "none"
            else:
                index = [index for index in range(len(clientAgentlist)) if clientAgentlist[index].lower() == clientAgent.lower()]            
                if len(index) == 1:
                    download_id = download_idlist[index[0]]
                    clientAgent = clientAgentlist[index[0]]
                    release_status = "snatched"
                    Logger.debug("Found download_id: %s for clientAgent: %s. Release status is: %s", download_id, clientAgent, release_status)
                else:
                    Logger.info("Found a total of %s releases snatched for clientAgent: %s. Cannot determine download_id. Will perform a renamenr scan to try and process.", len(index), clientAgent)                
                    download_id = "none"
                    release_status = "none"
        else: #something went wrong here.... we should never get to this.
            Logger.info("Could not find a download_id in the database for this movie")
            release_status = "none"
    except: # index out of range/doesn't exist?
        Logger.exception("Could not find a download_id for this movie")
        download_id = "none"
    return movie_status, clientAgent, download_id, release_status

def process(dirName, nzbName=None, status=0, clientAgent = "manual", download_id = ""):

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
    wait_for = int(config.get("CouchPotato", "wait_for"))

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

    try:
        remoteCPS = int(config.get("CouchPotato", "remoteCPS"))
    except (ConfigParser.NoOptionError, ValueError):
        remoteCPS = 0

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
    
    movie_id = get_movie_info(myOpener, baseURL, imdbid, download_id) # get the CPS database movie id this movie.
   
    initial_status, clientAgent, download_id, initial_release_status = get_status(myOpener, baseURL, movie_id, clientAgent, download_id)
    
    process_all_exceptions(nzbName.lower(), dirName)

    if status == 0:
        if transcode == 1:
            result = Transcoder.Transcode_directory(dirName)
            if result == 0:
                Logger.debug("Transcoding succeeded for files in %s", dirName)
            else:
                Logger.warning("Transcoding failed for files in %s", dirName)

        if method == "manage":
            command = "manage.update"
        else:
            command = "renamer.scan"
            if clientAgent != "manual" and download_id != "none":
                if remoteCPS == 1:
                    command = command + "/?downloader=" + clientAgent + "&download_id=" + download_id
                else:
                    command = command + "/?movie_folder=" + dirName + "&downloader=" + clientAgent + "&download_id=" + download_id

        url = baseURL + command

        Logger.info("Waiting for %s seconds to allow CPS to process newly extracted files", str(delay))

        time.sleep(delay)

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = myOpener.openit(url)
        except:
            Logger.exception("Unable to open URL")
            return 1 # failure

        result = json.load(urlObj)
        Logger.info("CouchPotatoServer returned %s", result)
        if result['success']:
            Logger.info("%s scan started on CouchPotatoServer for %s", method, nzbName)
        else:
            Logger.error("%s scan has NOT started on CouchPotatoServer for %s. Exiting", method, nzbName)
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
        except:
            Logger.exception("Unable to open URL")
            return 1 # failure

        result = urlObj.readlines()
        for line in result:
            Logger.info("%s", line)

        Logger.info("Movie %s set to try the next best release on CouchPotatoServer", movie_id)
        if delete_failed and not dirName in ['sys.argv[0]','/','']:
            Logger.info("Deleting failed files and folder %s", dirName)
            try:
                shutil.rmtree(dirName)
            except:
                Logger.exception("Unable to delete folder %s", dirName)
        return 0 # success
    
    if nzbName == "Manual Run":
        return 0 # success

    # we will now check to see if CPS has finished renaming before returning to TorrentToMedia and unpausing.
    start = datetime.datetime.now()  # set time for timeout
    pause_for = wait_for * 10 # keep this so we only ever have 6 complete loops.
    while (datetime.datetime.now() - start) < datetime.timedelta(minutes=wait_for):  # only wait 2 (default) minutes, then return.
        movie_status, clientAgent, download_id, release_status = get_status(myOpener, baseURL, movie_id, clientAgent, download_id) # get the current status fo this movie.
        if movie_status != initial_status:  # Something has changed. CPS must have processed this movie.
            Logger.info("SUCCESS: This movie is now marked as status %s in CouchPotatoServer", movie_status)
            return 0 # success
        time.sleep(pause_for) # Just stop this looping infinitely and hogging resources for 2 minutes ;)
    else:
        if release_status != initial_release_status and release_status != "none":  # Something has changed. CPS must have processed this movie.
            Logger.info("SUCCESS: This release is now marked as status %s in CouchPotatoServer", release_status)
            return 0 # success
        else: # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resule seeding now. 
            Logger.warning("The movie does not appear to have changed status after %s minutes. Please check CouchPotato Logs", wait_for)
            return 1 # failure
