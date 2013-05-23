#!/usr/bin/env python

#System imports
import os
import sys
import ConfigParser
import shutil
import logging
import datetime
import time
import re
from sets import Set
from subprocess import call

# Custom imports
import autoProcess.migratecfg as migratecfg
import extractor.extractor as extractor
import autoProcess.autoProcessComics as autoProcessComics
import autoProcess.autoProcessGames as autoProcessGames 
import autoProcess.autoProcessMusic as autoProcessMusic
import autoProcess.autoProcessTV as autoProcessTV
import autoProcess.autoProcessMovie as autoProcessMovie
from autoProcess.nzbToMediaEnv import *
from autoProcess.nzbToMediaUtil import *
from utorrent.client import UTorrentClient

def main(inputDirectory, inputName, inputCategory, inputHash, inputID):

    status = int(1)  # 1 = failed | 0 = success
    root = int(0)
    video = int(0)
    video2 = int(0)
    foundFile = int(0)
    numCompressed = int(0)
    extractionSuccess = False

    Logger.debug("MAIN: Received Directory: %s | Name: %s | Category: %s", inputDirectory, inputName, inputCategory)

    inputDirectory, inputName, inputCategory, root = category_search(inputDirectory, inputName, inputCategory, root, categories)  # Confirm the category by parsing directory structure

    for category in categories:
        if category == inputCategory:
            outputDestination = os.path.normpath(os.path.join(outputDirectory, category, safeName(inputName)))
            Logger.info("MAIN: Output directory set to: %s", outputDestination)
            break
        else:
            continue

    Logger.debug("MAIN: Scanning files in directory: %s", inputDirectory)      

    now = datetime.datetime.now()
    for dirpath, dirnames, filenames in os.walk(inputDirectory):
        for file in filenames:

            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)
            targetDirectory = os.path.join(outputDestination, file)

            if root == 1:
                if not foundFile: 
                    Logger.debug("MAIN: Looking for %s in: %s", inputName, file)
                if (safeName(inputName) in safeName(file)) or (safeName(os.path.splitext(file)[0]) in safeName(inputName)) and foundFile == 0:
                    pass  # This file does match the Torrent name
                    foundFile = 1
                    Logger.debug("MAIN: Found file %s that matches Torrent Name %s", file, inputName)
                else:
                    continue  # This file does not match the Torrent name, skip it

            if root == 2:
                Logger.debug("MAIN: Looking for files with modified/created dates less than 5 minutes old.")
                mtime_lapse = now - datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(dirpath, file)))
                ctime_lapse = now - datetime.datetime.fromtimestamp(os.path.getctime(os.path.join(dirpath, file)))
                if (mtime_lapse < datetime.timedelta(minutes=5)) or (ctime_lapse < datetime.timedelta(minutes=5)) and foundFile == 0:
                    pass  # This file does match the date time criteria
                    foundFile = 1
                    Logger.debug("MAIN: Found file %s with date modifed/created less than 5 minutes ago.", file)
                else:
                    continue  # This file has not been recently moved or created, skip it

            if not (inputCategory == cpsCategory or inputCategory == sbCategory): #process all for non-video categories.
                Logger.info("MAIN: Found file %s for category %s", filepath, inputCategory)
                copy_link(filePath, targetDirectory, useLink, outputDestination)
            elif fileExtension in mediaContainer:  # If the file is a video file
                if is_sample(filePath, inputName, minSampleSize):  # Ignore samples
                    Logger.info("MAIN: Ignoring sample file: %s  ", filePath)
                    continue
                else:
                    video = video + 1
                    Logger.info("MAIN: Found video file %s in %s", fileExtension, filePath)
                    try:
                        copy_link(filePath, targetDirectory, useLink, outputDestination)
                    except:
                        Logger.exception("MAIN: Failed to link file: %s", file)
            elif fileExtension in metaContainer:
                Logger.info("MAIN: Found metadata file %s for file %s", fileExtension, filePath)
                try:
                    copy_link(filePath, targetDirectory, useLink, outputDestination)
                except:
                    Logger.exception("MAIN: Failed to link file: %s", file)
            elif fileExtension in compressedContainer:
                numCompressed = numCompressed + 1
                if re.search(r'\d+', os.path.splitext(fileName)[1]) and numCompressed > 1: # find part numbers in second "extension" from right, if we have more than 1 compressed file.
                    part = int(re.search(r'\d+', os.path.splitext(fileName)[1]).group())
                    if part == 1: # we only want to extract the primary part.
                        Logger.debug("MAIN: Found primary part of a multi-part archive %s. Extracting", file)                       
                    else:
                        Logger.debug("MAIN: Found part %s of a multi-part archive %s. Ignoring", part, file)
                        continue
                Logger.info("MAIN: Found compressed archive %s for file %s", fileExtension, filePath)
                try:
                    extractor.extract(filePath, outputDestination)
                    extractionSuccess = True # we use this variable to determine if we need to pause a torrent or not in uTorrent (dont need to pause archived content)
                except:
                    Logger.exception("MAIN: Extraction failed for: %s", file)
            else:
                Logger.debug("MAIN: Ignoring unknown filetype %s for file %s", fileExtension, filePath)
                continue
    flatten(outputDestination)

    # Now check if movie files exist in destination:
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            fileExtension = os.path.splitext(file)[1]
            if fileExtension in mediaContainer:  # If the file is a video file
                if is_sample(filePath, inputName, minSampleSize):
                    Logger.debug("MAIN: Removing sample file: %s", filePath)
                    os.unlink(filePath)  # remove samples
                else:
                    video2 = video2 + 1
    if video2 >= video and video2 > 0:  # Check that all video files were moved
        status = 0

    # Hardlink solution for uTorrent, need to implent support for deluge, transmission
    if clientAgent == 'utorrent' and extractionSuccess == False and inputHash:
        try:
            Logger.debug("MAIN: Connecting to uTorrent: %s", uTorrentWEBui)
            utorrentClass = UTorrentClient(uTorrentWEBui, uTorrentUSR, uTorrentPWD)
        except:
            Logger.exception("MAIN: Failed to connect to uTorrent")

        # if we are using links with uTorrent it means we need to pause it in order to access the files
        if useLink != "no":
            Logger.debug("MAIN: Stoping torrent %s in uTorrent while processing", inputName)
            utorrentClass.stop(inputHash)
            time.sleep(5)  # Give uTorrent some time to catch up with the change

        # Delete torrent and torrentdata from uTorrent
        if deleteOriginal == 1:
            Logger.debug("MAIN: Deleting torrent %s from uTorrent", inputName)
            utorrentClass.removedata(inputHash)
            utorrentClass.remove(inputHash)
            time.sleep(5)

    processCategories = Set([cpsCategory, sbCategory, hpCategory, mlCategory, gzCategory])

    if inputCategory and not (inputCategory in processCategories): # no extra processign to be done... yet.
        Logger.info("MAIN: No further processing to be done for category %s.", inputCategory)
        result = 1
    elif status == 0:
        Logger.debug("MAIN: Calling autoProcess script for successful download.")
    else:
        Logger.error("MAIN: Something failed! Please check logs. Exiting")
        sys.exit(-1)

    if inputCategory == cpsCategory:
        Logger.info("MAIN: Calling CouchPotatoServer to post-process: %s", inputName)
        if clientAgent == 'utorrent' and inputHash != '':
            download_id = 'uTorrent_' + inputHash
        elif clientAgent == 'transmission' and inputHash != '':
            download_id = 'Transmission_' + inputHash
        else:
            download_id = inputHash
        result = autoProcessMovie.process(outputDestination, inputName, status, clientAgent, download_id)
    elif inputCategory == sbCategory:
        Logger.info("MAIN: Calling Sick-Beard to post-process: %s", inputName)
        result = autoProcessTV.processEpisode(outputDestination, inputName, status)
    elif inputCategory == hpCategory:
        Logger.info("MAIN: Calling HeadPhones to post-process: %s", inputName)
        result = autoProcessMusic.process(outputDestination, inputName, status)
    elif inputCategory == mlCategory:
        Logger.info("MAIN: Calling Mylar to post-process: %s", inputName)
        result = autoProcessComics.processEpisode(outputDestination, inputName, status)
    elif inputCategory == gzCategory:
        Logger.info("MAIN: Calling Gamez to post-process: %s", inputName)
        result = autoProcessGames.process(outputDestination, inputName, status)

    if result == 1:
        Logger.info("MAIN: A problem was reported in the autoProcess* script. If torrent was pasued we will resume seeding")

    # Hardlink solution for uTorrent, need to implent support for deluge, transmission
    if clientAgent == 'utorrent' and extractionSuccess == False and inputHash and useLink != "no" and deleteOriginal == 0: # we always want to resume seeding, for now manually find out what is wrong when extraction fails
        Logger.debug("MAIN: Starting torrent %s in uTorrent", inputName)
        utorrentClass.start(inputHash)

    Logger.info("MAIN: All done.")

if __name__ == "__main__":

    #check to migrate old cfg before trying to load.
    if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
        migratecfg.migrate()
    
    # Logging
    nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
    Logger = logging.getLogger(__name__)

    Logger.info("====================") # Seperate old from new log
    Logger.info("TorrentToMedia %s", VERSION)

    WakeUp()

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
    useLink = config.get("Torrent", "useLink")                                          # no | hard | sym
    outputDirectory = config.get("Torrent", "outputDirectory")                          # /abs/path/to/complete/
    categories = (config.get("Torrent", "categories")).split(',')                       # music,music_videos,pictures,software

    uTorrentWEBui = config.get("Torrent", "uTorrentWEBui")                              # http://localhost:8090/gui/
    uTorrentUSR = config.get("Torrent", "uTorrentUSR")                                  # mysecretusr
    uTorrentPWD = config.get("Torrent", "uTorrentPWD")                                  # mysecretpwr
    
    deleteOriginal = int(config.get("Torrent", "deleteOriginal"))                       # 0
    
    compressedContainer = (config.get("Extensions", "compressedExtensions")).split(',') # .zip,.rar,.7z
    mediaContainer = (config.get("Extensions", "mediaExtensions")).split(',')           # .mkv,.avi,.divx
    metaContainer = (config.get("Extensions", "metaExtensions")).split(',')             # .nfo,.sub,.srt
    minSampleSize = int(config.get("Extensions", "minSampleSize"))                      # 200 (in MB)
    
    cpsCategory = config.get("CouchPotato", "cpsCategory")                              # movie
    sbCategory = config.get("SickBeard", "sbCategory")                                  # tv
    hpCategory = config.get("HeadPhones", "hpCategory")                                 # music
    mlCategory = config.get("Mylar", "mlCategory")                                      # comics
    gzCategory = config.get("Gamez", "gzCategory")                                      # games
    categories.append(cpsCategory)
    categories.append(sbCategory)
    categories.append(hpCategory)
    categories.append(mlCategory)
    categories.append(gzCategory)
    
    transcode = int(config.get("Transcoder", "transcode"))

    try:
        inputDirectory, inputName, inputCategory, inputHash, inputID = parse_args(clientAgent)
    except:
        Logger.exception("MAIN: There was a problem loading variables")
        sys.exit(-1)

    main(inputDirectory, inputName, inputCategory, inputHash, inputID)
