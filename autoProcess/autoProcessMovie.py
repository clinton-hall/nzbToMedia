import urllib
import datetime
import json
import logging

import Transcoder
from nzbToMediaEnv import *
from nzbToMediaUtil import *
from nzbToMediaSceneExceptions import process_all_exceptions


Logger = logging.getLogger()
socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

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
        Logger.debug("Could not find an imdb id in directory or name")
        return ""

def get_movie_info(baseURL, imdbid, download_id):

    movie_id = ""
    movie_status = None
    release_status = None    
    if not imdbid and not download_id:
        return movie_id, imdbid, download_id, movie_status, release_status 

    releaselist = []
    movieid = []
    moviestatus = []
    library = []
    release = []
    offset = int(0)
    while True:
        url = baseURL + "media.list/?status=active&release_status=snatched&limit_offset=50," + str(offset)

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = urllib.urlopen(url)
        except:
            Logger.exception("Unable to open URL")
            break

        movieid2 = []
        library2 = []
        release2 = []
        moviestatus2 = []
        try:
            result = json.load(urlObj)
            movieid2 = [item["_id"] for item in result["movies"]]
            for item in result["movies"]:
                if "identifier" in item:
                    library2.append(item["identifier"])
                else:
                    library2.append(item["identifiers"]["imdb"])
            release2 = [item["releases"] for item in result["movies"]]
            moviestatus2 = [item["status"] for item in result["movies"]]
        except:
            Logger.exception("Unable to parse json data for movies")
            break

        movieid.extend(movieid2)
        moviestatus.extend(moviestatus2)
        library.extend(library2)
        release.extend(release2)
        if len(movieid2) < int(50): # finished parsing list of movies. Time to break.
            break
        offset = offset + 50

    result = None # reset
    for index in range(len(movieid)):
        releaselist1 = [item for item in release[index] if item["status"] == "snatched" and "download_info" in item]
        if download_id:
            releaselist = [item for item in releaselist1 if item["download_info"]["id"].lower() == download_id.lower()]
        else:
            releaselist = releaselist1

        if imdbid and library[index] == imdbid:
            movie_id = str(movieid[index])
            movie_status = str(moviestatus[index])
            Logger.info("Found movie id %s with status %s in CPS database for movie %s", movie_id, movie_status, imdbid)
            if not download_id and len(releaselist) == 1:
                download_id = releaselist[0]["download_info"]["id"]

        elif not imdbid and download_id and len(releaselist) > 0:
            movie_id = str(movieid[index])
            movie_status = str(moviestatus[index])
            imdbid = str(library[index])
            Logger.info("Found movie id %s and imdb %s with status %s in CPS database via download_id %s", movie_id, imdbid, movie_status, download_id)

        else:
            continue

        if len(releaselist) == 1:
            release_status = releaselist[0]["status"]
            Logger.debug("Found a single release with download_id: %s. Release status is: %s", download_id, release_status)

        break
           
    if not movie_id:
        Logger.exception("Could not parse database results to determine imdbid or movie id")

    return movie_id, imdbid, download_id, movie_status, release_status 

def get_status(baseURL, movie_id, download_id):
    result = None
    movie_status = None
    release_status = None    
    if not movie_id:
        return movie_status, release_status

    Logger.debug("Looking for status of movie: %s", movie_id)
    url = baseURL + "media.get/?id=" + str(movie_id)
    Logger.debug("Opening URL: %s", url)

    try:
        urlObj = urllib.urlopen(url)
    except:
        Logger.exception("Unable to open URL")
        return None, None  
    try:
        result = json.load(urlObj)
        movie_status = str(result["media"]["status"])
        Logger.debug("This movie is marked as status %s in CouchPotatoServer", movie_status)
    except:
        Logger.exception("Could not find a status for this movie")

    try:
        if len(result["media"]["releases"]) == 1 and result["media"]["releases"][0]["status"] == "done":
            release_status = result["media"]["releases"][0]["status"]
        else:
            release_status_list = [item["status"] for item in result["media"]["releases"] if "download_info" in item and item["download_info"]["id"].lower() == download_id.lower()]
            if len(release_status_list) == 1:
                release_status = release_status_list[0]
        Logger.debug("This release is marked as status %s in CouchPotatoServer", release_status)
    except: # index out of range/doesn't exist?
        Logger.exception("Could not find a status for this release")

    return movie_status, release_status

def process(dirName, nzbName=None, status=0, clientAgent = "manual", download_id = "", inputCategory=None):

    status = int(status)

    Logger.info("Loading config from %s", CONFIG_FILE)

    if not config():
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    section = "CouchPotato"
    if inputCategory != None and config().has_section(inputCategory):
        section = inputCategory

    host = config().get(section, "host")
    port = config().get(section, "port")
    apikey = config().get(section, "apikey")
    delay = float(config().get(section, "delay"))
    method = config().get(section, "method")
    delete_failed = int(config().get(section, "delete_failed"))
    wait_for = int(config().get(section, "wait_for"))
    try:
        TimePerGiB = int(config().get(section, "TimePerGiB"))
    except (config.NoOptionError, ValueError):
        TimePerGiB = 60 # note, if using Network to transfer on 100Mbit LAN, expect ~ 600 MB/minute.
    try:
        ssl = int(config().get(section, "ssl"))
    except (config.NoOptionError, ValueError):
        ssl = 0
    try:
        web_root = config().get(section, "web_root")
    except config.NoOptionError:
        web_root = ""
    try:    
        transcode = int(config().get("Transcoder", "transcode"))
    except (config.NoOptionError, ValueError):
        transcode = 0
    try:
        remoteCPS = int(config().get(section, "remoteCPS"))
    except (config.NoOptionError, ValueError):
        remoteCPS = 0

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
    
    movie_id, imdbid, download_id, initial_status, initial_release_status = get_movie_info(baseURL, imdbid, download_id) # get the CPS database movie id for this movie.
    
    process_all_exceptions(nzbName.lower(), dirName)
    nzbName, dirName = convert_to_ascii(nzbName, dirName)

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
            if clientAgent != "manual" and download_id != None:
                if remoteCPS == 1:
                    command = command + "/?downloader=" + clientAgent + "&download_id=" + download_id
                else:
                    command = command + "/?media_folder=" + urllib.quote(dirName) + "&downloader=" + clientAgent + "&download_id=" + download_id

        dirSize = getDirectorySize(dirName) # get total directory size to calculate needed processing time.
        TimeOut2 = int(TimePerGiB) * dirSize # Couchpotato needs to complete all moving and renaming before returning the status.
        TimeOut2 += 60 # Add an extra minute for over-head/processing/metadata.
        socket.setdefaulttimeout(int(TimeOut2)) #initialize socket timeout. We may now be able to remove the delays from the wait_for section below? If true, this should exit on first loop.

        url = baseURL + command

        Logger.info("Waiting for %s seconds to allow CPS to process newly extracted files", str(delay))

        time.sleep(delay)

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = urllib.urlopen(url)
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

        url = baseURL + "movie.searcher.try_next/?media_id=" + movie_id

        Logger.debug("Opening URL: %s", url)

        try:
            urlObj = urllib.urlopen(url)
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
    if not download_id:
        return 1 # just to be sure TorrentToMedia doesn't start deleting files as we havent verified changed status.

    # we will now check to see if CPS has finished renaming before returning to TorrentToMedia and unpausing.
    socket.setdefaulttimeout(int(TimeOut)) #initialize socket timeout.

    release_status = None
    start = datetime.datetime.now()  # set time for timeout
    pause_for = int(wait_for) * 10 # keep this so we only ever have 6 complete loops. This may not be necessary now?
    while (datetime.datetime.now() - start) < datetime.timedelta(minutes=wait_for):  # only wait 2 (default) minutes, then return.
        movie_status, release_status = get_status(baseURL, movie_id, download_id) # get the current status fo this movie.
        if movie_status and initial_status and movie_status != initial_status:  # Something has changed. CPS must have processed this movie.
            Logger.info("SUCCESS: This movie is now marked as status %s in CouchPotatoServer", movie_status)
            return 0 # success
        time.sleep(pause_for) # Just stop this looping infinitely and hogging resources for 2 minutes ;)
    else:
        if release_status and initial_release_status and release_status != initial_release_status:  # Something has changed. CPS must have processed this movie.
            Logger.info("SUCCESS: This release is now marked as status %s in CouchPotatoServer", release_status)
            return 0 # success
        else: # The status hasn't changed. we have waited 2 minutes which is more than enough. uTorrent can resule seeding now. 
            Logger.warning("The movie does not appear to have changed status after %s minutes. Please check CouchPotato Logs", wait_for)
            return 1 # failure
