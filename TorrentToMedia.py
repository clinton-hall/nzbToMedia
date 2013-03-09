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
import autoProcessComics
import autoProcessGames 
import autoProcessMusic
import autoProcessTV
import autoProcessMovie
import Transcoder
from nzbToMediaEnv import *
from nzbToMediaUtil import *
from utorrent.client import UTorrentClient

def main(inputDirectory, inputName, inputCategory, inputHash):

    status = int(1)  # 1 = failed | 0 = success
    root = int(0)
    video = int(0)
    video2 = int(0)

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
            fileExtension = os.path.splitext(file)[1]
            targetDirectory = os.path.join(outputDestination, file)

            if root == 1:
                Logger.debug("MAIN: Looking for %s in filename", inputName)
                if (safeName(inputName) in safeName(file)) or (safeName(os.path.splitext(file)[0]) in safeName(inputName)):
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

            if not (inputCategory == cpsCategory or inputCategory == sbCategory): #process all for non-video categories.
                Logger.info("MAIN: Found file %s for category %s", filepath, inputCategory)
                copy_link(filePath, targetDirectory, useLink, outputDestination
            elif fileExtension in mediaContainer:  # If the file is a video file
                if is_sample(filePath, inputName, minSampleSize):  # Ignore samples
                    Logger.info("MAIN: Ignoring sample file: %s  ", filePath)
                    continue
                else:
                    video = video + 1
                    Logger.info("MAIN: Found video file %s in %s", fileExtension, filePath)
                    try:
                        copy_link(filePath, targetDirectory, useLink, outputDestination)
                    except Exception as e:
                        Logger.error("MAIN: Failed to link file: %s", file)
                        Logger.debug(e)
            elif fileExtension in metaContainer:
                Logger.info("MAIN: Found metadata file %s for file %s", fileExtension, filePath)
                try:
                    copy_link(filePath, targetDirectory, useLink, outputDestination)
                except Exception as e:
                    Logger.error("MAIN: Failed to link file: %s", file)
                    Logger.debug(e)
            elif fileExtension in compressedContainer:
                Logger.info("MAIN: Found compressed archive %s for file %s", fileExtension, filePath)
                try:
                    extractor.extract(filePath, outputDestination)
                    extractionSuccess = True # we use this variable to determine if we need to pause a torrent or not in uTorrent (dont need to pause archived content)
                except Exception as e:
                    Logger.warn("MAIN: Extraction failed for: %s", file)
                    Logger.debug(e)
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
                    if transcode:
                        result = Transcoder.Transcode_file(filePath)
    if video2 >= video and video2 > 0:  # Check that all video files were moved
        status = 0

    processCategories = {cpsCategory, sbCategory, hpCategory, mlCategory}
    if inputCategory and not (inputCategory in processCategories): # no extra processign to be done... yet.
        Logger.info("MAIN: No further processing to be done for category %s.", inputCategory)
        Logger.info("MAIN: All done.")
        sys.exit(0)

    if status == 0: #### Maybe we should move this to a more appropriate place?
        Logger.info("MAIN: Successful run")
        Logger.debug("MAIN: Calling autoProcess script for successful download.")
    else:
        Logger.error("MAIN: Something failed! Please check logs. Exiting")
        sys.exit(-1)

    #### Delete original files from uTorrent
    if deleteOriginal and clientAgent == 'utorrent':
        try:
            Logger.debug("MAIN: Connecting to uTorrent: %s", uTorrentWEBui)
            utorrentClass = UTorrentClient(uTorrentWEBui, uTorrentUSR, uTorrentPWD)
        except Exception as e:
            Logger.error("MAIN: Failed to connect to uTorrent: %s", e)

        Logger.debug("MAIN: Deleting torrent %s from uTorrent", inputName)
        utorrentClass.stop(inputHash)
        time.sleep(5)  # Give uTorrent some time to catch up with the change

    #### quick 'n dirty hardlink solution for uTorrent, need to implent support for deluge, transmission
    if not extractionSuccess and inputHash and useLink and clientAgent == 'utorrent' and not deleteOriginal:
        try:
            Logger.debug("MAIN: Connecting to uTorrent: %s", uTorrentWEBui)
            utorrentClass = UTorrentClient(uTorrentWEBui, uTorrentUSR, uTorrentPWD)
        except Exception as e:
            Logger.error("MAIN: Failed to connect to uTorrent: %s", e)

        Logger.debug("MAIN: Stoping torrent %s in uTorrent while processing", inputName)
        utorrentClass.removedata(inputHash)
        time.sleep(5)  # Give uTorrent some time to catch up with the change
    ##### quick 'n dirty hardlink solution for uTorrent, need to implent support for deluge, transmission

    # Now we pass off to CouchPotato or Sick-Beard
    if inputCategory == cpsCategory:
        Logger.info("MAIN: Calling CouchPotatoServer to post-process: %s", inputName)
        result = autoProcessMovie.process(outputDestination, inputName, status)
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

    #### quick 'n dirty hardlink solution for uTorrent, need to implent support for deluge, transmission
    if not extractionSuccess and inputHash and useLink and clientAgent == 'utorrent' and not deleteOriginal: # we always want to resume seeding, for now manually find out what is wrong when extraction fails
        Logger.debug("MAIN: Starting torrent %s in uTorrent", inputName)
        utorrentClass.start(inputHash)
    #### quick 'n dirty hardlink solution for uTorrent, need to implent support for deluge, transmission
    
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
    useLink = config.get("Torrent", "useLink")                                          # true | false
    minSampleSize = int(config.get("Torrent", "minSampleSize"))                         # 200 (in MB)
    outputDirectory = config.get("Torrent", "outputDirectory")                          # /abs/path/to/complete/
    categories = (config.get("Torrent", "categories")).split(',')                       # music,music_videos,pictures,software

    uTorrentWEBui = config.get("Torrent", "uTorrentWEBui")                              # http://localhost:8090/gui/
    uTorrentUSR = config.get("Torrent", "uTorrentUSR")                                  # mysecretusr
    uTorrentPWD = config.get("Torrent", "uTorrentPWD")                                  # mysecretpwr
    
    deleteOriginal = config.get("Torrent", "deleteOriginal")                            # 0
    compressedContainer = (config.get("Torrent", "compressedExtensions")).split(',')    # .zip,.rar,.7z
    mediaContainer = (config.get("Torrent", "mediaExtensions")).split(',')              # .mkv,.avi,.divx
    metaContainer = (config.get("Torrent", "metaExtensions")).split(',')                # .nfo,.sub,.srt
    keepExtensions = (config.get("Torrent", "keepExtensions")).split(',')               # .mp3,.jpg,.exe
    
    cpsCategory = config.get("CouchPotato", "cpsCategory")                              # movie
    sbCategory = config.get("SickBeard", "sbCategory")                                  # tv
    hpCategory = config.get("HeadPhones", "hpCategory")                                 # music
    mlCategory = config.get("Mylar", "mlCategory")                                      # comics
    gzCategory = config.get("Gamez", "gzCategory")
    categories.append(cpsCategory)
    categories.append(sbCategory)
    categories.append(hpCategory)
    categories.append(mlCategory)
    categories.append(gzCategory)
    
    transcode = config.get("Transcoder", "transcode")

    try:
        inputDirectory, inputName, inputCategory, inputHash = parse_args(clientAgent)
    except Exception as e:
        Logger.error("MAIN: There was a problem loading variables: %s", e)
        sys.exit(-1)

    main(inputDirectory, inputName, inputCategory, inputHash)
