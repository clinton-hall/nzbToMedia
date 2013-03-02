#!/usr/bin/env python

#System imports
import ConfigParser
import sys
import os
import shutil
import logging
import datetime
import time
from subprocess import call


# Custom imports
import extractor.extractor as extractor
import autoProcessMovie
import autoProcessTV
from nzbToMediaEnv import *
from nzbToMediaUtil import *
from utorrent.client import UTorrentClient

def main(inputDirectory, inputName, inputCategory, inputHash)

    status = int(1)  # 1 = failed | 0 = success
    root = int(0)
    video = int(0)
    video2 = int(0)

    Logger.debug("MAIN: Received Directory: %s | Name: %s | Category: %s", inputDirectory, inputName, inputCategory)

    inputDirectory, inputName, inputCategory, root = category_search(inputDirectory, inputName, inputCategory, root, categories)  # Confirm the category by parsing directory structure
    if inputCategory == movieCategory:
        outputDestination = os.path.normpath(os.path.join(movieDestination, inputName))
    elif inputCategory == tvCategory:
        outputDestination = os.path.normpath(os.path.join(tvDestination, inputName))
    else:
        Logger.error("MAIN: Category of %s does not match either %s or %s: Exiting", inputCategory, movieCategory, tvCategory)
        Logger.debug("MAIN: Future versions of this script might do something for Category: %s. Keep updating ;)", inputCategory)
        sys.exit(-1)

    Logger.debug("MAIN: Scanning files in directory: %s", inputDirectory)      

    now = datetime.datetime.now()
    for dirpath, dirnames, filenames in os.walk(inputDirectory):
        for file in filenames:

            filePath = os.path.join(dirpath, file)
            fileExtention = os.path.splitext(file)[1]
            targetDirectory = os.path.join(outputDestination, file)

            if root == 1:
                Logger.debug("MAIN: Looking for %s in filename", inputName)
                if (inputName in file) or (os.path.splitext(file)[0] in inputName):
                    pass  # This file does match the Torrent name
                    Logger.debug("Found file %s that matches Torrent Name %s", file, inputName)
                else:
                    continue  # This file does not match the Torrent name, skip it

            if root == 2:
                Logger.debug("MAIN: Looking for files with modified/created dates less than 5 minutes old.")
                mtime_lapse = now - datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(dirpath, file)))
                ctime_lapse = now - datetime.datetime.fromtimestamp(os.path.getctime(os.path.join(dirpath, file)))
                if (mtime_lapse < datetime.timedelta(minutes=5)) or (ctime_lapse < datetime.timedelta(minutes=5)):
                    pass  # This file does match the date time criteria
                    Logger.debug("Found file %s with date modifed/created less than 5 minutes ago.", file)
                else:
                    continue  # This file has not been recently moved or created, skip it

            if fileExtention in mediaContainer:  # If the file is a video file
                if is_sample(filePath, inputName, minSampleSize):  # Ignore samples
                    Logger.info("MAIN: Ignoring sample file: %s  ", filePath)
                    continue
                else:
                    video = video + 1
                    Logger.info("MAIN: Found video file %s in %s", fileExtention, filePath)
                    try:
                        copy_link(filePath, targetDirectory, useLink, outputDestination)
                    except Exception as e:
                        Logger.error("MAIN: Failed to link file %s", file)
                        Logger.debug e
                        linkFailed = True

            elif fileExtention in metaContainer:
                Logger.info("MAIN: Found metadata file %s for file %s", fileExtention, filePath)
                try:
                    copy_link(filePath, targetDirectory, useLink, outputDestination)
                except Exception as e:
                    Logger.error("MAIN: Failed to link file %s", file)
                    Logger.debug e
                    linkFailed = True

            elif fileExtention in compressedContainer:
                Logger.info("MAIN: Found compressed archive %s for file %s", fileExtention, filePath)
                try:
                    extractor.extract(filePath, outputDestination)
                except Exception as e:
                    Logger.warn("Extraction failed for: %s", file)
                    Logger.debug e
                    extractFailed = True

            else:
                Logger.debug("MAIN: Ignoring unknown filetype %s for file %s", fileExtention, filePath)
                continue
    flatten(outputDestination)

    # Now check if movie files exist in destination:
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            fileExtention = os.path.splitext(file)[1]
            if fileExtention in mediaContainer:  # If the file is a video file
                if is_sample(filePath, inputName, minSampleSize):
                    Logger.debug("Removing sample file: %s", filePath)
                    os.unlink(filePath)  # remove samples
                else:
                    videofile = filePath
                    video2 = video2 + 1
    if video2 >= video and video2 > 0:  # Check that all video files were moved
        status = 0

    if status == 0: #### Maybe we should move this to a more appropriate place?
        Logger.info("MAIN: Successful run")
        Logger.debug("MAIN: Calling autoProcess script for successful download.")
    elif extractFailed and linkFailed == False:  # failed to extract files only.
        Logger.info("MAIN: Failed to extract a compressed archive")
        Logger.debug("MAIN: Assume this to be password protected file.")
        Logger.debug("MAIN: Calling autoProcess script for failed download.")
    else:
        Logger.error("MAIN: Something failed! Please check logs. Exiting")
        sys.exit(-1)

    #### quick 'n dirt hardlink solution for uTorrent, need to implent support for deluge, transmission
    if inputHash and useLink and clientAgent == 'utorrent':
        try:
            Logger.debug("MAIN: Connecting to uTorrent: %s", uTorrentWEBui)
            utorrentClass = UTorrentClient(uTorrentWEBui, uTorrentUSR, uTorrentPWD)
        except Exception as e:
            Logger.error("MAIN: Failed to connect to uTorrent: %s", e)

        Logger.debug("MAIN: Stoping torrent %s in uTorrent while processing", inputName)
        utorrentClass.stop(inputHash)
        time.sleep(5)  # Give uTorrent some time to catch up with the change
    ##### quick 'n dirt hardlink solution for uTorrent, need to implent support for deluge, transmission

    # Now we pass off to CouchPotato or Sick-Beard
    if inputCategory == movieCategory:
        Logger.info("MAIN: Calling CouchPotatoServer to post-process: %s", inputName)  # can we use logger while logfile open?
        autoProcessMovie.process(outputDestination, inputName, status)
    elif inputCategory == tvCategory:
        Logger.info("MAIN: Calling Sick-Beard to post-process: %s", inputName)  # can we use logger while logfile open?
        autoProcessTV.processEpisode(outputDestination, inputName, status)

    # Check if the file still exists in the post-process directory
    now = datetime.datetime.now()  # set time for timeout
    while os.path.exists(outputDestination):  # while this directory is still here, CPS hasn't finished renaming
        if (datetime.datetime.now() - now) > datetime.timedelta(minutes=3):  # note; minimum 1 minute delay in autoProcessMovie
            Logger.info("MAIN: The directory %s has not been moved after 3 minutes.", outputDestination)
            break
        time.sleep(10) #Just stop this looping infinitely and hogging resources for 3 minutes ;)
    else:  # CPS (and SickBeard) have finished. We can now resume seeding.
        Logger.info("MAIN: Post-process appears to have succeeded for: %s", inputName)

    #### quick 'n dirt hardlink solution for uTorrent, need to implent support for deluge, transmission
    if inputHash and useLink and clientAgent == 'utorrent':
        Logger.debug("MAIN: Starting torrent %s in uTorrent", inputName)
        utorrentClass.start(inputHash)
    #### quick 'n dirt hardlink solution for uTorrent, need to implent support for deluge, transmission
    
    Logger.info("MAIN: All done.")

if __name__ == "__main__":

    # Logging
    nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
    Logger = logging.getLogger(__name__)

    Logger.info("====================") # Seperate old from new log
    Logger.info("TorrentToMedia %s", VERSION)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        sys.exit(-1)

    # CONFIG FILE
    Logger.info("MAIN: Loading config from %s", configFilename)
    config.read(configFilename)
                                                                                        # EXAMPLE VALUES:
    clientAgent = config.get("Torrent", "clientAgent")                                  # utorrent | deluge | transmission | other
    # SICK-BEARD
    tvCategory = config.get("SickBeard", "category")                                    # tv
    tvDestination = os.path.normpath(config.get("SickBeard", "outputDirectory"))        # C:\downloaded\tv | /path/to/downloaded/tv
    # COUCHPOTATOSERVER
    movieCategory = config.get("CouchPotato", "category")                               # movie
    movieDestination = os.path.normpath(config.get("CouchPotato", "outputDirectory"))   # C:\downloaded\movies | /path/to/downloaded/movies
    # TORRENTS
    useLink = config.get("Torrent", "useLink")                                          # true | false
    minSampleSize = int(config.get("Torrent", "minSampleSize"))                         # 200 (in MB)
    uTorrentWEBui = config.get("Torrent", "uTorrentWEBui")                              # http://localhost:8090/gui/
    uTorrentUSR = config.get("Torrent", "uTorrentUSR")                                  # mysecretusr
    uTorrentPWD = config.get("Torrent", "uTorrentPWD")                                  # mysecretpwr
    compressedContainer = (config.get("Torrent", "compressedExtentions")).split(',')    # .zip,.rar,.7z
    mediaContainer = (config.get("Torrent", "mediaExtentions")).split(',')              # .mkv,.avi,.divx
    metaContainer = (config.get("Torrent", "metaExtentions")).split(',')                # .nfo,.sub,.srt
    categories = (config.get("Torrent", "categories")).split(',')                       # music,music_videos,pictures,software
    categories.append(movieCategory)
    categories.append(tvCategory)  # now have a list of all categories in use.
    
    try:
        inputDirectory, inputName, inputCategory, inputHash = parse_args(clientAgent)
    except Exception as e:
        Logger.error("MAIN: There was a problem loading variables: %s", e)
        sys.exit(-1)

    main(inputDirectory, inputName, inputCategory, inputHash)
