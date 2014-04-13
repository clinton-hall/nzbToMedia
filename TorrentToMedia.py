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
from nzbtomedia.autoProcess.autoProcessComics import autoProcessComics
from nzbtomedia.autoProcess.autoProcessGames import autoProcessGames
from nzbtomedia.autoProcess.autoProcessMovie import autoProcessMovie
from nzbtomedia.autoProcess.autoProcessMusic import autoProcessMusic
from nzbtomedia.autoProcess.autoProcessTV import autoProcessTV
from nzbtomedia.extractor import extractor
from nzbtomedia.nzbToMediaUtil import category_search, safeName, is_sample, copy_link, parse_args, flatten, get_dirnames, \
    remove_read_only, cleanup_directories, create_torrent_class
from nzbtomedia import logger

def processTorrent(inputDirectory, inputName, inputCategory, inputHash, inputID):
    status = int(1)  # 1 = failed | 0 = success
    root = int(0)
    video = int(0)
    archive = int(0)
    foundFile = int(0)
    extracted_folder = []
    copy_list = []

    logger.debug("Received Directory: %s | Name: %s | Category: %s", inputDirectory, inputName, inputCategory)

    inputDirectory, inputName, inputCategory, root, single = category_search(inputDirectory, inputName, inputCategory, root, nzbtomedia.CATEGORIES)  # Confirm the category by parsing directory structure

    logger.debug("Determined Directory: %s | Name: %s | Category: %s", inputDirectory, inputName, inputCategory)

    TorrentClass = create_torrent_class(nzbtomedia.CLIENTAGENT)
    pause_torrent(nzbtomedia.CLIENTAGENT, TorrentClass, inputHash, inputID, inputName)

    processCategories = nzbtomedia.CFG[nzbtomedia.SECTIONS].sections

    if inputCategory == "":
        inputCategory = "UNCAT"
    outputDestination = os.path.normpath(os.path.join(nzbtomedia.OUTPUTDIRECTORY, inputCategory, safeName(inputName)))
    logger.postprocess("Output directory set to: %s", outputDestination)

    if nzbtomedia.CFG["SickBeard"][inputCategory]:
        Torrent_NoLink = int(nzbtomedia.CFG["SickBeard"][inputCategory]["Torrent_NoLink"])  # 0
        if Torrent_NoLink == 1:
            logger.postprocess("Calling autoProcessTV to post-process: %s",inputName)
            result = autoProcessTV().processEpisode(inputDirectory, inputName, 0, clientAgent=nzbtomedia.CLIENTAGENT, inputCategory=inputCategory)
            if result != 0:
                logger.error("A problem was reported in the autoProcessTV script.")
            resume_torrent(nzbtomedia.CLIENTAGENT, TorrentClass, inputHash, inputID, result, inputName)
            cleanup_directories(inputCategory, processCategories, result, outputDestination)
            return result

    processOnly = nzbtomedia.CFG[nzbtomedia.SECTIONS].sections
    if not "NONE" in nzbtomedia.USER_SCRIPT_CATEGORIES: # if None, we only process the 5 listed.
        if "ALL" in nzbtomedia.USER_SCRIPT_CATEGORIES: # All defined categories
            processOnly = nzbtomedia.CATEGORIES
        processOnly.extend(nzbtomedia.USER_SCRIPT_CATEGORIES) # Adds all categories to be processed by userscript.

    if not inputCategory in processOnly:
        logger.postprocess("No processing to be done for category: %s. Exiting", inputCategory)
        return

    logger.debug("Scanning files in directory: %s", inputDirectory)

    if nzbtomedia.CFG["HeadPhones"][inputCategory]:
        nzbtomedia.NOFLATTEN.extend(nzbtomedia.CFG["HeadPhones"].sections) # Make sure we preserve folder structure for HeadPhones.

    outputDestinationMaster = outputDestination # Save the original, so we can change this within the loop below, and reset afterwards.
    now = datetime.datetime.now()
    if single: inputDirectory,filename = os.path.split(inputDirectory)
    for dirpath, dirnames, filenames in os.walk(inputDirectory):
        if single:
            dirnames[:] = [] 
            filenames[:] = [filenames]  # we just want to work with this one file if single = True
        logger.debug("Found %s files in %s", str(len(filenames)), dirpath)
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)
            if inputCategory in nzbtomedia.NOFLATTEN and not single:
                newDir = dirpath # find the full path
                newDir = newDir.replace(inputDirectory, "") #find the extra-depth directory
                if len(newDir) > 0 and newDir[0] == "/":
                    newDir = newDir[1:] # remove leading "/" to enable join to work.
                outputDestination = os.path.join(outputDestinationMaster, newDir) # join this extra directory to output.
                logger.debug("Setting outputDestination to %s to preserve folder structure", outputDestination)

            targetDirectory = os.path.join(outputDestination, file)

            if root == 1:
                if foundFile == int(0):
                    logger.debug("Looking for %s in: %s", inputName, file)
                if (safeName(inputName) in safeName(file)) or (safeName(fileName) in safeName(inputName)):
                    #pass  # This file does match the Torrent name
                    foundFile = 1
                    logger.debug("Found file %s that matches Torrent Name %s", file, inputName)
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
                    logger.debug("Found file %s with date modifed/created less than 5 minutes ago.", file)
                else:
                    continue  # This file has not been recently moved or created, skip it

            if fileExtension in nzbtomedia.MEDIACONTAINER and is_sample(filePath, inputName, nzbtomedia.MINSAMPLESIZE,
                                                                        nzbtomedia.SAMPLEIDS) and not nzbtomedia.CFG["HeadPhones"][inputCategory]:   # Ignore samples
                logger.postprocess("Ignoring sample file: %s  ", filePath)
                continue

            if fileExtension in nzbtomedia.COMPRESSEDCONTAINER:
                if not (nzbtomedia.CFG["SickBeard"][inputCategory] and nzbtomedia.CFG["SickBeard"][inputCategory]["nzbExtractionBy"] == "Destination"):
                    # find part numbers in second "extension" from right, if we have more than 1 compressed file in the same directory.
                    if re.search(r'\d+', os.path.splitext(fileName)[1]) and os.path.dirname(filePath) in extracted_folder and not any(item in os.path.splitext(fileName)[1] for item in ['.720p','.1080p','.x264']):
                        part = int(re.search(r'\d+', os.path.splitext(fileName)[1]).group())
                        if part == 1: # we only want to extract the primary part.
                            logger.debug("Found primary part of a multi-part archive %s. Extracting", file)
                        else:
                            logger.debug("Found part %s of a multi-part archive %s. Ignoring", part, file)
                            continue
                    logger.postprocess("Found compressed archive %s for file %s", fileExtension, filePath)
                    try:
                        extractor.extract(filePath, outputDestination)
                        extractionSuccess = True # we use this variable to determine if we need to pause a torrent or not in uTorrent (don't need to pause archived content)
                        extracted_folder.append(os.path.dirname(filePath))
                    except:
                        logger.error("Extraction failed for: %s", file)
                    continue

            try:
                copy_link(filePath, targetDirectory, nzbtomedia.USELINK, outputDestination)
                copy_list.append([filePath, os.path.join(outputDestination, file)])
            except:
                logger.error("Failed to link file: %s", file)

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
                    logger.debug("Found media file: %s", filePath)
                    video += 1
                if fileExtension in nzbtomedia.COMPRESSEDCONTAINER:  # If the file is an archive file
                    archive += 1
        if video > int(0):  # Check that media files exist
            logger.debug("Found %s media files", str(video))
            status = int(0)
        elif not (nzbtomedia.CFG["SickBeard"][inputCategory] and nzbtomedia.CFG["SickBeard"][inputCategory]["nzbExtractionBy"] == "Destination") and archive > int(0):
            logger.debug("Found %s archive files to be extracted by SickBeard", str(archive))
            status = int(0)
        else:
            logger.warning("Found no media files in output.")

    if (inputCategory in nzbtomedia.USER_SCRIPT_CATEGORIES and not "NONE" in nzbtomedia.USER_SCRIPT_CATEGORIES) or ("ALL" in nzbtomedia.USER_SCRIPT_CATEGORIES and not inputCategory in processCategories):
        logger.postprocess("Processing user script %s.", nzbtomedia.USER_SCRIPT)
        result = external_script(outputDestination,inputName,inputCategory)
    elif status == int(0) or (nzbtomedia.CFG['HeadPhones','Mylar','Gamez'][inputCategory]): # if movies linked/extracted or for other categories.
        logger.debug("Calling autoProcess script for successful download.")
        status = int(0) # hp, my, gz don't support failed.
    else:
        logger.error("Something failed! Please check logs. Exiting")
        return status

    result = 0
    if nzbtomedia.CFG['CouchPotato'][inputCategory]:
        logger.postprocess("Calling CouchPotato:" + inputCategory + " to post-process: %s", inputName)
        download_id = inputHash
        result = autoProcessMovie().process(outputDestination, inputName, status, nzbtomedia.CLIENTAGENT, download_id, inputCategory)
    elif nzbtomedia.CFG['SickBeard'][inputCategory]:
        logger.postprocess("Calling Sick-Beard:" + inputCategory + " to post-process: %s", inputName)
        result = autoProcessTV().processEpisode(outputDestination, inputName, status, nzbtomedia.CLIENTAGENT, inputCategory)
    elif nzbtomedia.CFG['NzbDrone'][inputCategory]:
        logger.postprocess("Calling NzbDrone:" + inputCategory + " to post-process: %s", inputName)
        result = autoProcessTV().processEpisode(outputDestination, inputName, status, nzbtomedia.CLIENTAGENT, inputCategory)
    elif nzbtomedia.CFG['HeadPhones'][inputCategory]:
        logger.postprocess("Calling HeadPhones:" + inputCategory + " to post-process: %s", inputName)
        result = autoProcessMusic().process(inputDirectory, inputName, status, nzbtomedia.CLIENTAGENT, inputCategory)
    elif nzbtomedia.CFG['Mylar'][inputCategory]:
        logger.postprocess("Calling Mylar:" + inputCategory + " to post-process: %s", inputName)
        result = autoProcessComics().processEpisode(outputDestination, inputName, status, nzbtomedia.CLIENTAGENT, inputCategory)
    elif nzbtomedia.CFG['Gamez'][inputCategory]:
        logger.postprocess("Calling Gamez:" + inputCategory + " to post-process: %s", inputName)
        result = autoProcessGames().process(outputDestination, inputName, status, nzbtomedia.CLIENTAGENT, inputCategory)

    if result == 1:
        logger.error("A problem was reported in the autoProcess* script. If torrent was paused we will resume seeding")

    resume_torrent(nzbtomedia.CLIENTAGENT, TorrentClass, inputHash, inputID, result, inputName)
    cleanup_directories(inputCategory, processCategories, result, outputDestination)
    return result

def pause_torrent(clientAgent, TorrentClass, inputHash, inputID, inputName):
    # if we are using links with Torrents it means we need to pause it in order to access the files
    logger.debug("Stoping torrent %s in %s while processing", inputName, clientAgent)
    if clientAgent == 'utorrent' and TorrentClass != "":
        TorrentClass.stop(inputHash)
    if clientAgent == 'transmission' and TorrentClass !="":
        TorrentClass.stop_torrent(inputID)
    if clientAgent == 'deluge' and TorrentClass != "":
        TorrentClass.core.pause_torrent([inputID])
    time.sleep(5)  # Give Torrent client some time to catch up with the change

def resume_torrent(clientAgent, TorrentClass, inputHash, inputID, result, inputName):
    # Hardlink solution for uTorrent, need to implent support for deluge, transmission
    if clientAgent in ['utorrent', 'transmission', 'deluge']  and inputHash:
        # Delete torrent and torrentdata from Torrent client if processing was successful.
        if (int(nzbtomedia.CFG["Torrent"]["deleteOriginal"]) is 1 and result != 1) or nzbtomedia.USELINK == 'move': # if we move files, nothing to resume seeding.
            logger.debug("Deleting torrent %s from %s", inputName, clientAgent)
            if clientAgent == 'utorrent' and TorrentClass != "":
                TorrentClass.removedata(inputHash)
                TorrentClass.remove(inputHash)
            if clientAgent == 'transmission' and TorrentClass !="":
                TorrentClass.remove_torrent(inputID, True)
            if clientAgent == 'deluge' and TorrentClass != "":
                TorrentClass.core.remove_torrent(inputID, True)
        # we always want to resume seeding, for now manually find out what is wrong when extraction fails
        else:
            logger.debug("Starting torrent %s in %s", inputName, clientAgent)
            if clientAgent == 'utorrent' and TorrentClass != "":
                TorrentClass.start(inputHash)
            if clientAgent == 'transmission' and TorrentClass !="":
                TorrentClass.start_torrent(inputID)
            if clientAgent == 'deluge' and TorrentClass != "":
                TorrentClass.core.resume_torrent([inputID])
        time.sleep(5)

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
                logger.postprocess("Running script %s on file %s.", cmd, filePath)
                try:
                    p = Popen(command)
                    res = p.wait()
                    if str(res) in nzbtomedia.USER_SCRIPT_SUCCESSCODES: # Linux returns 0 for successful.
                        logger.postprocess("UserScript %s was successfull", command[0])
                        result = int(0)
                    else:
                        logger.error("UserScript %s has failed with return code: %s", command[0], res)
                        logger.postprocess("If the UserScript completed successfully you should add %s to the user_script_successCodes", res)
                        result = int(1)
                except:
                    logger.error("UserScript %s has failed", command[0])
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
        logger.postprocess("All files have been processed. Cleaning outputDirectory %s", outputDestination)
        shutil.rmtree(outputDestination)
    elif nzbtomedia.USER_SCRIPT_CLEAN == int(1) and num_files_new != int(0):
        logger.postprocess("%s files were processed, but %s still remain. outputDirectory will not be cleaned.", num_files, num_files_new)
    return final_result

def main():
    # Initialize the config
    nzbtomedia.initialize()

    logger.postprocess("#########################################################")
    logger.postprocess("## ..::[%s]::.. :: STARTING", os.path.splitext(os.path.basename(os.path.normpath(os.path.abspath(__file__))))[0])
    logger.postprocess("#########################################################")

    # debug command line options
    logger.debug("Options passed into TorrentToMedia: " + str(sys.argv))

    # Post-Processing Result
    result = 0

    try:
        inputDirectory, inputName, inputCategory, inputHash, inputID = parse_args(nzbtomedia.CLIENTAGENT)
    except:
        logger.error("There was a problem loading variables")
        return -1

        # check if this is a manual run
    if inputDirectory is None:
        logger.warning("Invalid number of arguments received from client, Switching to manual run mode ...")
        for section, subsection in nzbtomedia.SUBSECTIONS.items():
            for category in subsection:
                if nzbtomedia.CFG[section][category].isenabled():
                    dirNames = get_dirnames(section, category)
                    for dirName in dirNames:
                        logger.postprocess("Running %s:%s as a manual run for folder %s ...", section, category, dirName)
                        results = processTorrent(dirName, os.path.basename(dirName), category, inputHash, inputID)
                        if results != 0:
                            result = results
                            logger.error("A problem was reported when trying to manually run %s:%s.", section, category)
                else:
                    logger.warning("%s:%s is DISABLED, you can enable this in autoProcessMedia.cfg ...", section, category)
    else:
        result = processTorrent(inputDirectory, inputName, inputCategory, inputHash, inputID)

    logger.postprocess("All done.")
    return result
if __name__ == "__main__":
    exit(main())