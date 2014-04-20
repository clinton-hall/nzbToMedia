#!/usr/bin/env python
import datetime
import os
import time
import re
import shutil
import sys
import nzbtomedia
import platform

from subprocess import Popen
from nzbtomedia.Transcoder import Transcoder
from nzbtomedia.autoProcess.autoProcessComics import autoProcessComics
from nzbtomedia.autoProcess.autoProcessGames import autoProcessGames
from nzbtomedia.autoProcess.autoProcessMovie import autoProcessMovie
from nzbtomedia.autoProcess.autoProcessMusic import autoProcessMusic
from nzbtomedia.autoProcess.autoProcessTV import autoProcessTV
from nzbtomedia.extractor import extractor
from nzbtomedia.nzbToMediaUtil import category_search, sanitizeFileName, is_sample, copy_link, parse_args, flatten, get_dirnames, \
    remove_read_only, cleanup_directories, create_torrent_class, pause_torrent, resume_torrent, listMediaFiles
from nzbtomedia import logger

def processTorrent(inputDirectory, inputName, inputCategory, inputHash, inputID, clientAgent):
    status = int(1)  # 1 = failed | 0 = success
    root = int(0)
    video = int(0)
    archive = int(0)
    foundFile = int(0)
    extracted_folder = []
    copy_list = []

    logger.debug("Received Directory: %s | Name: %s | Category: %s" % (inputDirectory, inputName, inputCategory))

    inputDirectory, inputName, inputCategory, root, single = category_search(inputDirectory, inputName, inputCategory, root, nzbtomedia.CATEGORIES)  # Confirm the category by parsing directory structure

    logger.debug("Determined Directory: %s | Name: %s | Category: %s" % (inputDirectory, inputName, inputCategory))

    TorrentClass = None
    if clientAgent != 'manual':
        TorrentClass = create_torrent_class(clientAgent)
        pause_torrent(clientAgent, TorrentClass, inputHash, inputID, inputName)

    processCategories = nzbtomedia.CFG[nzbtomedia.SECTIONS].sections

    if inputCategory == "":
        inputCategory = "UNCAT"
    outputDestination = os.path.normpath(os.path.join(nzbtomedia.OUTPUTDIRECTORY, inputCategory, sanitizeFileName(inputName)))
    logger.info("Output directory set to: %s" % (outputDestination))

    if nzbtomedia.CFG["SickBeard"][inputCategory]:
        Torrent_NoLink = int(nzbtomedia.CFG["SickBeard"][inputCategory]["Torrent_NoLink"])  # 0
        if Torrent_NoLink == 1:
            status = 0
            # Check video files for corruption
            for video in listMediaFiles(inputDirectory):
                if not Transcoder().isVideoGood(video):
                    status = 1

            logger.info("Calling autoProcessTV to post-process: %s",inputName)
            result = autoProcessTV().processEpisode(inputDirectory, inputName, status, clientAgent=clientAgent, inputCategory=inputCategory)
            if result != 0:
                logger.error("A problem was reported in the autoProcessTV script.")

            if clientAgent != 'manual':
                resume_torrent(clientAgent, TorrentClass, inputHash, inputID, result, inputName)

            cleanup_directories(inputCategory, processCategories, result, outputDestination)
            return result

    processOnly = nzbtomedia.CFG[nzbtomedia.SECTIONS].sections
    if not "NONE" in nzbtomedia.USER_SCRIPT_CATEGORIES: # if None, we only process the 5 listed.
        if "ALL" in nzbtomedia.USER_SCRIPT_CATEGORIES: # All defined categories
            processOnly = nzbtomedia.CATEGORIES
        processOnly.extend(nzbtomedia.USER_SCRIPT_CATEGORIES) # Adds all categories to be processed by userscript.

    if not inputCategory in processOnly:
        logger.info("No processing to be done for category: %s. Exiting" % (inputCategory))
        return

    logger.debug("Scanning files in directory: %s" % (inputDirectory))

    if nzbtomedia.CFG["HeadPhones"][inputCategory]:
        nzbtomedia.NOFLATTEN.extend(nzbtomedia.CFG["HeadPhones"].sections) # Make sure we preserve folder structure for HeadPhones.

    outputDestinationMaster = outputDestination # Save the original, so we can change this within the loop below, and reset afterwards.
    now = datetime.datetime.now()
    if single: inputDirectory,filename = os.path.split(inputDirectory)
    for dirpath, dirnames, filenames in os.walk(inputDirectory):
        if single:
            dirnames[:] = [] 
            filenames[:] = [filenames]  # we just want to work with this one file if single = True
        logger.debug("Found %s files in %s" % (str(len(filenames)), dirpath))
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)
            if inputCategory in nzbtomedia.NOFLATTEN and not single:
                newDir = dirpath # find the full path
                newDir = newDir.replace(inputDirectory, "") #find the extra-depth directory
                if len(newDir) > 0 and newDir[0] == "/":
                    newDir = newDir[1:] # remove leading "/" to enable join to work.
                outputDestination = os.path.join(outputDestinationMaster, newDir) # join this extra directory to output.
                logger.debug("Setting outputDestination to %s to preserve folder structure" % (outputDestination))

            targetDirectory = os.path.join(outputDestination, file)

            if root == 1:
                if foundFile == int(0):
                    logger.debug("Looking for %s in: %s" % (inputName, file))
                if (sanitizeFileName(inputName) in sanitizeFileName(file)) or (sanitizeFileName(fileName) in sanitizeFileName(inputName)):
                    #pass  # This file does match the Torrent name
                    foundFile = 1
                    logger.debug("Found file %s that matches Torrent Name %s" % (file, inputName))
                else:
                    continue  # This file does not match the Torrent name, skip it

            if root == 2:
                if foundFile == int(0):
                    logger.debug("Looking for files with modified/created dates less than 5 minutes old.")
                mtime_lapse = now - datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(dirpath, file)))
                ctime_lapse = now - datetime.datetime.fromtimestamp(os.path.getctime(os.path.join(dirpath, file)))
                if (mtime_lapse < datetime.timedelta(minutes=5)) or (ctime_lapse < datetime.timedelta(minutes=5)):
                    #pass  # This file does match the date time criteria
                    foundFile = 1
                    logger.debug("Found file %s with date modifed/created less than 5 minutes ago." % (file))
                else:
                    continue  # This file has not been recently moved or created, skip it

            if fileExtension in nzbtomedia.MEDIACONTAINER and is_sample(filePath, inputName, nzbtomedia.MINSAMPLESIZE,
                                                                        nzbtomedia.SAMPLEIDS) and not nzbtomedia.CFG["HeadPhones"][inputCategory]:   # Ignore samples
                logger.info("Ignoring sample file: %s  " % (filePath))
                continue

            if fileExtension in nzbtomedia.COMPRESSEDCONTAINER:
                if not (nzbtomedia.CFG["SickBeard"][inputCategory] and nzbtomedia.CFG["SickBeard"][inputCategory]["nzbExtractionBy"] == "Destination"):
                    # find part numbers in second "extension" from right, if we have more than 1 compressed file in the same directory.
                    if re.search(r'\d+', os.path.splitext(fileName)[1]) and os.path.dirname(filePath) in extracted_folder and not any(item in os.path.splitext(fileName)[1] for item in ['.720p','.1080p','.x264']):
                        part = int(re.search(r'\d+', os.path.splitext(fileName)[1]).group())
                        if part == 1: # we only want to extract the primary part.
                            logger.debug("Found primary part of a multi-part archive %s. Extracting" % (file))
                        else:
                            logger.debug("Found part %s of a multi-part archive %s. Ignoring" % (part, file))
                            continue
                    logger.info("Found compressed archive %s for file %s" % (fileExtension, filePath))
                    try:
                        extractor.extract(filePath, outputDestination)
                        extractionSuccess = True # we use this variable to determine if we need to pause a torrent or not in uTorrent (don't need to pause archived content)
                        extracted_folder.append(os.path.dirname(filePath))
                    except:
                        logger.error("Extraction failed for: %s" % (file))
                    continue

            try:
                copy_link(filePath, targetDirectory, nzbtomedia.USELINK, outputDestination)
                copy_list.append([filePath, os.path.join(outputDestination, file)])
            except:
                logger.error("Failed to link file: %s" % (file))

    outputDestination = outputDestinationMaster # Reset here.
    if not inputCategory in nzbtomedia.NOFLATTEN: #don't flatten hp in case multi cd albums, and we need to copy this back later.
        flatten(outputDestination)

    if platform.system().lower() == 'windows':  # remove Read Only flag from files in Windows.
        remove_read_only(outputDestination)

    # Now check if video files exist in destination:
    if nzbtomedia.CFG["SickBeard","NzbDrone", "CouchPotato"][inputCategory]:
        for dirpath, dirnames, filenames in os.walk(outputDestination):
            for file in filenames:
                filePath = os.path.join(dirpath, file)
                fileName, fileExtension = os.path.splitext(file)
                if fileExtension in nzbtomedia.MEDIACONTAINER:  # If the file is a video file
                    logger.debug("Found media file: %s" % (filePath))
                    video += 1
                if fileExtension in nzbtomedia.COMPRESSEDCONTAINER:  # If the file is an archive file
                    archive += 1
        if video > int(0):  # Check that media files exist
            logger.debug("Found %s media files" % (str(video)))
            status = int(0)
        elif not (nzbtomedia.CFG["SickBeard"][inputCategory] and nzbtomedia.CFG["SickBeard"][inputCategory]["nzbExtractionBy"] == "Destination") and archive > int(0):
            logger.debug("Found %s archive files to be extracted by SickBeard" % (str(archive)))
            status = int(0)
        else:
            logger.warning("Found no media files in output.")

    if (inputCategory in nzbtomedia.USER_SCRIPT_CATEGORIES and not "NONE" in nzbtomedia.USER_SCRIPT_CATEGORIES) or ("ALL" in nzbtomedia.USER_SCRIPT_CATEGORIES and not inputCategory in processCategories):
        logger.info("Processing user script %s." % (nzbtomedia.USER_SCRIPT))
        result = external_script(outputDestination,inputName,inputCategory)
    elif status == int(0) or (nzbtomedia.CFG['HeadPhones','Mylar','Gamez'][inputCategory]): # if movies linked/extracted or for other categories.
        logger.debug("Calling autoProcess script for successful download.")
        status = int(0) # hp, my, gz don't support failed.
    else:
        logger.error("Something failed! Please check logs. Exiting")
        return status

    result = 0

    # Check video files for corruption
    for video in listMediaFiles(inputDirectory):
        if not Transcoder().isVideoGood(video):
            status = 1

    if nzbtomedia.CFG['CouchPotato'][inputCategory]:
        logger.info("Calling CouchPotato:" + inputCategory + " to post-process: %s" % (inputName))
        download_id = inputHash
        result = autoProcessMovie().process(outputDestination, inputName, status, clientAgent, download_id, inputCategory)
    elif nzbtomedia.CFG['SickBeard'][inputCategory]:
        logger.info("Calling Sick-Beard:" + inputCategory + " to post-process: %s" % (inputName))
        result = autoProcessTV().processEpisode(outputDestination, inputName, status, clientAgent, inputCategory)
    elif nzbtomedia.CFG['NzbDrone'][inputCategory]:
        logger.info("Calling NzbDrone:" + inputCategory + " to post-process: %s" % (inputName))
        result = autoProcessTV().processEpisode(outputDestination, inputName, status, clientAgent, inputCategory)
    elif nzbtomedia.CFG['HeadPhones'][inputCategory]:
        logger.info("Calling HeadPhones:" + inputCategory + " to post-process: %s" % (inputName))
        result = autoProcessMusic().process(outputDestination, inputName, status, clientAgent, inputCategory)
    elif nzbtomedia.CFG['Mylar'][inputCategory]:
        logger.info("Calling Mylar:" + inputCategory + " to post-process: %s" % (inputName))
        result = autoProcessComics().processEpisode(outputDestination, inputName, status, clientAgent, inputCategory)
    elif nzbtomedia.CFG['Gamez'][inputCategory]:
        logger.info("Calling Gamez:" + inputCategory + " to post-process: %s" % (inputName))
        result = autoProcessGames().process(outputDestination, inputName, status, clientAgent, inputCategory)

    if result == 1 and clientAgent != 'manual':
        logger.error("A problem was reported in the autoProcess* script. If torrent was paused we will resume seeding")

    if clientAgent != 'manual':
        resume_torrent(clientAgent, TorrentClass, inputHash, inputID, result, inputName)

    cleanup_directories(inputCategory, processCategories, result, outputDestination)
    return result

def external_script(outputDestination, torrentName, torrentLabel):

    final_result = int(0) # start at 0.
    num_files = int(0)
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:

            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS or "ALL" in nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS:
                num_files = num_files + 1
                if nzbtomedia.USER_SCRIPT_RUNONCE == 1 and num_files > 1: # we have already run once, so just continue to get number of files.
                    continue
                command = [nzbtomedia.USER_SCRIPT]
                for param in nzbtomedia.USER_SCRIPT_PARAM:
                    if param == "FN":
                        command.append(file)
                        continue
                    elif param == "FP":
                        command.append(filePath)
                        continue
                    elif param == "TN":
                        command.append(torrentName)
                        continue
                    elif param == "TL":
                        command.append(torrentLabel)
                        continue
                    elif param == "DN":
                        if nzbtomedia.USER_SCRIPT_RUNONCE == 1:
                            command.append(outputDestination)
                        else:
                            command.append(dirpath)
                        continue
                    else:
                        command.append(param)
                        continue
                cmd = ""
                for item in command:
                    cmd = cmd + " " + item
                logger.info("Running script %s on file %s." % (cmd, filePath))
                try:
                    p = Popen(command)
                    res = p.wait()
                    if str(res) in nzbtomedia.USER_SCRIPT_SUCCESSCODES: # Linux returns 0 for successful.
                        logger.info("UserScript %s was successfull" % (command[0]))
                        result = int(0)
                    else:
                        logger.error("UserScript %s has failed with return code: %s" % (command[0], res))
                        logger.info("If the UserScript completed successfully you should add %s to the user_script_successCodes" % (res))
                        result = int(1)
                except:
                    logger.error("UserScript %s has failed" % (command[0]))
                    result = int(1)
                final_result = final_result + result

    time.sleep(nzbtomedia.USER_DELAY)
    num_files_new = int(0)
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS or nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS == "ALL":
                num_files_new = num_files_new + 1

    if nzbtomedia.USER_SCRIPT_CLEAN == int(1) and num_files_new == int(0) and final_result == int(0):
        logger.info("All files have been processed. Cleaning outputDirectory %s" % (outputDestination))
        shutil.rmtree(outputDestination)
    elif nzbtomedia.USER_SCRIPT_CLEAN == int(1) and num_files_new != int(0):
        logger.info("%s files were processed, but %s still remain. outputDirectory will not be cleaned." % (num_files, num_files_new))
    return final_result

def main(args):
    # Initialize the config
    nzbtomedia.initialize()

    # clientAgent for Torrents
    clientAgent = nzbtomedia.TORRENT_CLIENTAGENT

    logger.info("#########################################################")
    logger.info("## ..::[%s]::.. CLIENT:%s ## STARTING" % (args[0], clientAgent))
    logger.info("#########################################################")

    # debug command line options
    logger.debug("Options passed into TorrentToMedia: %s" % (args))

    # Post-Processing Result
    result = 0


    try:
        inputDirectory, inputName, inputCategory, inputHash, inputID = parse_args(clientAgent, args)
    except:
        logger.error("There was a problem loading variables")
        return -1

    if inputDirectory and inputName and inputHash and inputID:
        result = processTorrent(inputDirectory, inputName, inputCategory, inputHash, inputID, clientAgent)
    else:
        # Perform Manual Run
        logger.warning("Invalid number of arguments received from client, Switching to manual run mode ...")

        # Loop and auto-process
        clientAgent = 'manual'
        for section, subsection in nzbtomedia.SUBSECTIONS.items():
            for category in subsection:
                if nzbtomedia.CFG[section][category].isenabled():
                    dirNames = get_dirnames(section, category)
                    for dirName in dirNames:
                        logger.info("Running %s:%s as a manual run for folder %s ..." % (section, category, dirName))
                        results = processTorrent(dirName, os.path.basename(dirName), category, inputHash, inputID, clientAgent)
                        if results != 0:
                            result = results
                            logger.error("A problem was reported when trying to manually run %s:%s." % (section, category))
                else:
                    logger.warning("%s:%s is DISABLED, you can enable this in autoProcessMedia.cfg ..." % (section, category))

    if result == 0:
        logger.info("The %s script completed successfully." % (args[0]))
    else:
        logger.error("A problem was reported in the %s script." % (args[0]))

    sys.exit(result)

if __name__ == "__main__":
    main(sys.argv)
