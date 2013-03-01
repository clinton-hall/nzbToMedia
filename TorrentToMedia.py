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
import linktastic.linktastic as linktastic
import extractor.extractor as extractor
import autoProcessMovie
import autoProcessTV
from nzbToMediaEnv import *
from nzbToMediaUtil import *
from utorrent.client import UTorrentClient

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)


def category_search(inputDirectory, inputName, inputCategory, root, categories):
    categorySearch = [os.path.normpath(inputDirectory), ""]  # initializie
    notfound = 0
    for x in range(10):  # loop up through 10 directories looking for category.
        try:
            categorySearch2 = os.path.split(os.path.normpath(categorySearch[0]))
        except:  # this might happen when we can't go higher.
            if inputCategory and inputName:  # if these exists, we are ok to proceed, but assume we are in a root/common directory.
                Logger.info("SEARCH: Could not find a Torrent Name or category in the directory structure")
                Logger.info("SEARCH: We assume the directory passed is the root directory for your downlaoder")
                Logger.warn("SEARCH: You should change settings to download torrents to their own directory if possible")
                Logger.info("SEARCH: We will try and determine which files to process, individually")
                root = 1
                break  # we are done
            elif inputCategory:  # if this exists, we are ok to proceed, but assume we are in a root/common directory and we have to check file dates.
                Logger.info("SEARCH: Could not find a Torrent Name or Category in the directory structure")
                Logger.info("SEARCH: We assume the directory passed is the root directory for your downlaoder")
                Logger.warn("SEARCH: You should change settings to download torrents to their own directory if possible")
                Logger.info("SEARCH: We will try and determine which files to process, individually")
                root = 2
                break  # we are done
            else:
                Logger.error("SEARCH: Could not identify Category of Torrent Name in the directory structure. Please check downloader settings. Exiting")
                sys.exit(-1)

        if categorySearch2[1] in categories:
            Logger.debug("SEARCH: Found Category: %s in directory structure", categorySearch2[1])
            if not inputCategory:
                Logger.info("SEARCH: Determined Category to be: %s", categorySearch2[1])
                inputCategory = categorySearch2[1]
            if inputName and categorySearch[0] != os.path.normpath(inputDirectory):  # if we are not in the root directory and we have inputName we can continue.
                if ('.cp(tt' in categorySearch[1]) and (not '.cp(tt' in inputName):  # if the directory was created by CouchPotato, and this tag is not in Torrent name, we want to add it.
                    Logger.info("SEARCH: Changing Torrent Name to %s to preserve imdb id.", categorySearch[1])
                    inputName = categorySearch[1]
                    Logger.info("SEARCH: Identified Category: %s and Torrent Name: %s. We are in a unique directory, so we can proceed.", inputCategory, inputName)
                    break  # we are done
            elif categorySearch[1] and not inputName:  # assume the the next directory deep is the torrent name.
                Logger.info("SEARCH: Found torrent directory %s in category directory %s", os.path.join(categorySearch[0], categorySearch[1]), categorySearch[0])
                inputName = categorySearch[1]
                break  # we are done
            elif ('.cp(tt' in categorySearch[1]) and (not '.cp(tt' in inputName):  # if the directory was created by CouchPotato, and this tag is not in Torrent name, we want to add it.
                Logger.info("SEARCH: Changing Torrent Name to %s to preserve imdb id.", categorySearch[1])
                inputName = categorySearch[1]
                break  # we are done
            elif os.path.isdir(os.path.join(categorySearch[0], inputName)) and inputName:  # testing for torrent name in first sub directory
                Logger.info("SEARCH: Found torrent directory %s in category directory %s", os.path.join(categorySearch[0], inputName), categorySearch[0])
                if categorySearch[0] == os.path.normpath(inputDirectory):  # only true on first pass, x =0
                    inputDirectory = os.path.join(categorySearch[0], inputName)  # we only want to search this next dir up.
                break  # we are done
            elif inputName:  # if these exists, we are ok to proceed, but we are in a root/common directory.
                Logger.info("SEARCH: Could not find a unique torrent folder in the directory structure")
                Logger.info("SEARCH: The directory passed is the root directory for category %s", categorySearch2[1])
                Logger.warn("SEARCH: You should change settings to download torrents to their own directory if possible")
                Logger.info("SEARCH: We will try and determine which files to process, individually")
                root = 1
                break  # we are done
            else:  # this is a problem! if we don't have Torrent name and are in the root category dir, we can't proceed.
                Logger.warn("SEARCH: Could not identify a torrent name and the directory passed is common to all downloads for category %s.", categorySearch[1])
                Logger.warn("SEARCH: You should change settings to download torrents to their own directory if possible")
                Logger.info("SEARCH: We will try and determine which files to process, individually")
                root = 2
                break
        elif categorySearch2[1] == inputName and inputName:  # we have identified a unique directory.
            Logger.info("SEARCH: Files appear to be in their own directory")
            if inputCategory:  # we are ok to proceed.
                break  # we are done
            else:
                Logger.debug("SEARCH: Continuing scan to determin category.")
                categorySearch = categorySearch2  # ready for next loop
                continue  # keep going
        else:
            if x == 9:  # This is the last pass in the loop and we didn't find anything.
                notfound = 1
                break    # we are done
            else:
                categorySearch = categorySearch2  # ready for next loop
                continue   # keep going

    if notfound == 1:
        if inputCategory and inputName:  # if these exists, we are ok to proceed, but assume we are in a root/common directory.
            Logger.info("SEARCH: Could not find a category in the directory structure")
            Logger.info("SEARCH: We assume the directory passed is the root directory for your downlaoder")
            Logger.warn("SEARCH: You should change settings to download torrents to their own directory if possible")
            Logger.info("SEARCH: We will try and determine which files to process, individually")
            root = 1
        elif inputCategory:  # if this exists, we are ok to proceed, but assume we are in a root/common directory and we have to check file dates.
            Logger.info("SEARCH: Could not find a Torrent Name or Category in the directory structure")
            Logger.info("SEARCH: We assume the directory passed is the root directory for your downlaoder")
            Logger.warn("SEARCH: You should change settings to download torrents to their own directory if possible")
            Logger.info("SEARCH: We will try and determine which files to process, individually")
            root = 2
    if not inputCategory:  # we didn't find this after 10 loops. This is a problem.
            Logger.error("SEARCH: Could not identify category and torrent name from the directory structure. Please check downloader settings. Exiting")
            sys.exit(-1)  # Oh yeah.... WE ARE DONE!

    return inputDirectory, inputName, inputCategory, root


def is_sample(filePath, inputName):
    # 200 MB in bytes
    SIZE_CUTOFF = minSampleSize * 1024 * 1024
    # Ignore 'sample' in files unless 'sample' in Torrent Name
    return ('sample' in filePath.lower()) and (not 'sample' in inputName) and (os.path.getsize(filePath) < SIZE_CUTOFF)


def create_destination(outputDestination):
    if not os.path.exists(outputDestination):
        try:
            Logger.info("CREATE DESTINATION: Creating destination folder: %s", outputDestination)
            os.makedirs(outputDestination)
        except Exception, e:
            Logger.error("CREATE DESTINATION: Not possible to create destination folder: %s", e)
            return False


def copy_link(source, target, useLink, outputDestination):
    create_destination(outputDestination)
    if useLink:
        try:
            Logger.info("COPYLINK: Linking %s to %s", source, target)
            linktastic.link(source, target)
        except:
            if os.path.isfile(target):
                Logger.info("COPYLINK: Something went wrong in linktastic.link, but the destination file was created")
            else:
                Logger.info("COPYLINK: Something went wrong in linktastic.link, copying instead")
                Logger.debug("COPYLINK: Copying %s to %s", source, target)
                shutil.copy(source, target)
    else:
        Logger.debug("Copying %s to %s", source, target)
        shutil.copy(source, target)
    return True


def flatten(outputDestination):
    Logger.info("FLATTEN: Flattening directory: %s", outputDestination)
    for dirpath, dirnames, filenames in os.walk(outputDestination):  # Flatten out the directory to make postprocessing easier
        if dirpath == outputDestination:
            continue  # No need to try and move files in the root destination directory
        for filename in filenames:
            source = os.path.join(dirpath, filename)
            target = os.path.join(outputDestination, filename)
            try:
                shutil.move(source, target)
            except OSError:
                Logger.error("FLATTEN: Could not flatten %s", source)
    removeEmptyFolders(outputDestination)  # Cleanup empty directories


def removeEmptyFolders(path):
    Logger.info("REMOVER: Removing empty folders in: %s", path)
    if not os.path.isdir(path):
        return

    # Remove empty subfolders
    files = os.listdir(path)
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                removeEmptyFolders(fullpath)

    # If folder empty, delete it
    files = os.listdir(path)
    if len(files) == 0:
        Logger.debug("REMOVER: Removing empty folder: %s", path)
        os.rmdir(path)

Logger.info("==========================") # Seperate old from new log
Logger.info("TorrentToMedia %s", VERSION)
config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")

### TORRENT TO MEDIA ###
if not os.path.isfile(configFilename):
    Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
    sys.exit(-1)

Logger.info("MAIN: Loading config from %s", configFilename)
config.read(configFilename)

clientAgent = config.get("Torrent", "clientAgent")

try:
    inputDirectory, inputName, inputCategory, inputHash = parse_args(clientAgent)
except:
    Logger.error("MAIN: There was a problem loading variables: Exiting")
    sys.exit(-1)

#### Main routine starts here.

Logger.debug("MAIN: Received Directory: %s | Name: %s | Category: %s", inputDirectory, inputName, inputCategory)

# Sick-Beard
tvCategory = config.get("SickBeard", "category")
tvDestination = os.path.normpath(config.get("SickBeard", "outputDirectory"))
# CouchPotatoServer
movieCategory = config.get("CouchPotato", "category")
movieDestination = os.path.normpath(config.get("CouchPotato", "outputDirectory"))
# Torrent specific
useLink = config.get("Torrent", "useLink")
minSampleSize = int(config.get("Torrent", "minSampleSize"))
uTorrentWEBui = config.get("Torrent", "uTorrentWEBui")
uTorrentUSR = config.get("Torrent", "uTorrentUSR")
uTorrentPWD = config.get("Torrent", "uTorrentPWD")
compressedContainer = (config.get("Torrent", "compressedExtentions")).split(',')
mediaContainer = (config.get("Torrent", "mediaExtentions")).split(',')
metaContainer = (config.get("Torrent", "metaExtentions")).split(',')
categories = (config.get("Torrent", "categories")).split(',')
categories.append(movieCategory)
categories.append(tvCategory)  # now have a list of all categories in use.

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
            if is_sample(filePath, inputName):  # Ignore samples
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
            if is_sample(filePath, inputName):
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
