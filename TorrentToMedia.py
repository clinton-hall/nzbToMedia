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

# Logging
nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

def main()

    Logger.info("==========================") # Seperate old from new log
    Logger.info("TorrentToMedia %s", VERSION)
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        sys.exit(-1)

    Logger.info("MAIN: Loading config from %s", configFilename)
    config.read(configFilename)

                                                                                        # EXAMPLE VALUES:
    clientAgent = config.get("Torrent", "clientAgent")                                  # utorrent | deluge | transmission | other
    # Sick-Beard
    tvCategory = config.get("SickBeard", "category")                                    # tv
    tvDestination = os.path.normpath(config.get("SickBeard", "outputDirectory"))        # C:\downloaded\tv | /path/to/downloaded/tv
    # CouchPotatoServer
    movieCategory = config.get("CouchPotato", "category")                               # movie
    movieDestination = os.path.normpath(config.get("CouchPotato", "outputDirectory"))   # C:\downloaded\movies | /path/to/downloaded/movies
    # Torrent specific
    useLink = config.get("Torrent", "useLink")                                          # true | false
    minSampleSize = int(config.get("Torrent", "minSampleSize"))                         # 200
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
    except:
        Logger.error("MAIN: There was a problem loading variables: Exiting")
        sys.exit(-1)

    Logger.debug("MAIN: Received Directory: %s | Name: %s | Category: %s", inputDirectory, inputName, inputCategory)

    status = int(1)  # We start as "failed" until we verify movie file in destination
    root = int(0)
    video = int(0)
    video2 = int(0)
    failed_link = int(0)
    failed_extract = int(0)

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
    if root == 1:
        Logger.debug("MAIN: Looking for %s in filename", inputName)
    elif root == 2:
        Logger.debug("MAIN: Looking for files with modified/created dates less than 5 minutes old.")

    now = datetime.datetime.now()
    for dirpath, dirnames, filenames in os.walk(inputDirectory):
        for file in filenames:
            if root == 1:
                if (inputName in file) or (os.path.splitext(file)[0] in inputName):
                    pass  # This file does match the Torrent name
                    Logger.debug("Found file %s that matches Torrent Name %s", file, inputName)
                else:
                    continue  # This file does not match the Torrent name, skip it
            if root == 2:
                mtime_lapse = now - datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(dirpath, file)))
                ctime_lapse = now - datetime.datetime.fromtimestamp(os.path.getctime(os.path.join(dirpath, file)))
                if (mtime_lapse < datetime.timedelta(minutes=5)) or (ctime_lapse < datetime.timedelta(minutes=5)):
                    pass  # This file does match the date time criteria
                    Logger.debug("Found file %s with date modifed/created less than 5 minutes ago.", file)
                else:
                    continue  # This file has not been recently moved or created, skip it
            filePath = os.path.join(dirpath, file)
            fileExtention = os.path.splitext(file)[1]
            if fileExtention in mediaContainer:  # If the file is a video file
                if is_sample(filePath, inputName, minSampleSize):  # Ignore samples
                    Logger.info("MAIN: Ignoring sample file: %s  ", filePath)
                    continue
                else:
                    video = video + 1
                    source = filePath
                    target = os.path.join(outputDestination, file)
                    Logger.info("MAIN: Found video file %s in %s", fileExtention, filePath)
                    state = copy_link(source, target, useLink, outputDestination)
                    if state == False:
                        Logger.error("MAIN: Failed to link file %s", file)
                        failed_link = 1
            elif fileExtention in metaContainer:
                source = filePath
                target = os.path.join(outputDestination, file)
                Logger.info("MAIN: Found metadata file %s for file %s", fileExtention, filePath)
                state = copy_link(source, target, useLink, outputDestination)
                if state == False:
                    Logger.error("MAIN: Failed to link file %s", file)
                    failed_link = 1
            elif fileExtention in compressedContainer:
                Logger.info("MAIN: Found compressed archive %s for file %s", fileExtention, filePath)
                source = filePath
                target = os.path.join(outputDestination, file)
                try:
                    extractor.extract(dirpath, file, outputDestination)
                except:
                    Logger.warn("Extraction failed for %s", file)
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
    elif failed_extract == 1 and failed_link == 0:  # failed to extract files only.
        Logger.info("MAIN: Failed to extract a compressed archive")
        Logger.debug("MAIN: Assume this to be password protected file.")
        Logger.debug("MAIN: Calling autoProcess script for failed download.")
    else:
        Logger.error("MAIN: Something failed! Please check logs. Exiting")
        sys.exit(-1)

    # Hardlink solution with uTorrent
    if inputHash and useLink:
        try:
            Logger.debug("MAIN: Connecting to uTorrent: %s", uTorrentWEBui)
            utorrentClass = UTorrentClient(uTorrentWEBui, uTorrentUSR, uTorrentPWD)
        except:
            Logger.error("MAIN: Failed to connect to uTorrent")

        Logger.debug("MAIN: Stoping torrent %s in uTorrent while processing", videofile)
        utorrentClass.stop(inputHash)
        time.sleep(5)  # Give uTorrent some time to catch up with the change

    # Now we pass off to CouchPotato or Sick-Beard
    if inputCategory == movieCategory:
        Logger.info("MAIN: Calling CouchPotatoServer to post-process: %s", videofile)  # can we use logger while logfile open?
        autoProcessMovie.process(outputDestination, inputName, status)
    elif inputCategory == tvCategory:
        Logger.info("MAIN: Calling Sick-Beard to post-process: %s", videofile)  # can we use logger while logfile open?
        autoProcessTV.processEpisode(outputDestination, inputName, status)

    # Check if the file still exists in the post-process directory
    now = datetime.datetime.now()  # set time for timeout
    while os.path.exists(videofile):  # while this file is still here, CPS hasn't finished renaming
        if (datetime.datetime.now() - now) > datetime.timedelta(minutes=3):  # note; minimum 1 minute delay in autoProcessMovie
            Logger.info("MAIN: The file %s has not been moved after 3 minutes.", videofile)
            break
        time.sleep(10) #Just stop this looping infinitely and hogging resources for 3 minutes ;)
    else:  # CPS (and SickBeard) have finished. We can now resume seeding.
        Logger.info("MAIN: Post-process appears to have succeeded for: %s", videofile)

    # Hardlink solution with uTorrent
    if inputHash and useLink:
        Logger.debug("MAIN: Starting torrent %s in uTorrent", inputName)
        utorrentClass.start(inputHash)

if __name__ == "__main__":
    main()
