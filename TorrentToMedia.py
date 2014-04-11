#!/usr/bin/env python
# adds lib directory to system path
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib')))

import datetime
import time
import logging
import re
import shutil
from subprocess import Popen
from nzbtomedia.autoProcess.autoProcessComics import autoProcessComics
from nzbtomedia.autoProcess.autoProcessGames import autoProcessGames
from nzbtomedia.autoProcess.autoProcessMovie import autoProcessMovie
from nzbtomedia.autoProcess.autoProcessMusic import autoProcessMusic
from nzbtomedia.autoProcess.autoProcessTV import autoProcessTV
from nzbtomedia.extractor import extractor
from nzbtomedia.nzbToMediaAutoFork import autoFork
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaUtil import category_search, safeName, is_sample, copy_link, WakeUp, parse_args, flatten, \
    nzbtomedia_configure_logging, get_dirnames
from nzbtomedia.synchronousdeluge.client import DelugeClient
from nzbtomedia.utorrent.client import UTorrentClient
from nzbtomedia.transmissionrpc.client import Client as TransmissionClient

def main(inputDirectory, inputName, inputCategory, inputHash, inputID):

    status = int(1)  # 1 = failed | 0 = success
    root = int(0)
    video = int(0)
    archive = int(0)
    foundFile = int(0)
    extracted_folder = []
    extractionSuccess = False
    copy_list = []
    file = None

    Logger.debug("MAIN: Received Directory: %s | Name: %s | Category: %s", inputDirectory, inputName, inputCategory)

    inputDirectory, inputName, inputCategory, root, single = category_search(inputDirectory, inputName, inputCategory, root, categories)  # Confirm the category by parsing directory structure

    Logger.debug("MAIN: Determined Directory: %s | Name: %s | Category: %s", inputDirectory, inputName, inputCategory)

    TorrentClass = create_torrent_class(clientAgent, inputHash)
    pause_torrent(clientAgent, TorrentClass, inputHash, inputID, inputName)

    processCategories = config()[sections].sections

    outputDestination = ""
    if inputCategory == "":
        inputCategory = "UNCAT"
    outputDestination = os.path.normpath(os.path.join(outputDirectory, inputCategory, safeName(inputName)))
    Logger.info("MAIN: Output directory set to: %s", outputDestination)

    if config()["SickBeard"].issubsection(inputCategory):
        Torrent_NoLink = int(config()["SickBeard"][inputCategory]["Torrent_NoLink"])  # 0
        if Torrent_NoLink == 1:
            Logger.info("MAIN: Calling autoProcessTV to post-process: %s",inputName)
            result = autoProcessTV().processEpisode(inputDirectory, inputName, 0, clientAgent=clientAgent, inputCategory=inputCategory)
            if result != 0:
                Logger.info("MAIN: A problem was reported in the autoProcessTV script.")
            resume_torrent(clientAgent, TorrentClass, inputHash, inputID, result, inputName)
            cleanup_output(inputCategory, processCategories, result, outputDestination)
            Logger.info("MAIN: All done.")
            sys.exit()

    processOnly = config()[sections].sections
    if not "NONE" in user_script_categories: # if None, we only process the 5 listed.
        if "ALL" in user_script_categories: # All defined categories
            processOnly = categories
        processOnly.extend(user_script_categories) # Adds all categories to be processed by userscript.

    if not inputCategory in processOnly:
        Logger.info("MAIN: No processing to be done for category: %s. Exiting", inputCategory)
        Logger.info("MAIN: All done.")
        sys.exit()

    Logger.debug("MAIN: Scanning files in directory: %s", inputDirectory)

    if config()["HeadPhones"].issubsection(inputCategory):
        noFlatten.extend(config()["HeadPhones"].sections) # Make sure we preserve folder structure for HeadPhones.

    outputDestinationMaster = outputDestination # Save the original, so we can change this within the loop below, and reset afterwards.
    now = datetime.datetime.now()
    if single: inputDirectory,filename = os.path.split(inputDirectory)
    for dirpath, dirnames, filenames in os.walk(inputDirectory):
        if single:
            dirnames[:] = [] 
            filenames[:] = [filenames]  # we just want to work with this one file if single = True
        Logger.debug("MAIN: Found %s files in %s", str(len(filenames)), dirpath)
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)
            if inputCategory in noFlatten and not single:
                newDir = dirpath # find the full path
                newDir = newDir.replace(inputDirectory, "") #find the extra-depth directory
                if len(newDir) > 0 and newDir[0] == "/":
                    newDir = newDir[1:] # remove leading "/" to enable join to work.
                outputDestination = os.path.join(outputDestinationMaster, newDir) # join this extra directory to output.
                Logger.debug("MAIN: Setting outputDestination to %s to preserve folder structure", outputDestination)

            targetDirectory = os.path.join(outputDestination, file)

            if root == 1:
                if foundFile == int(0):
                    Logger.debug("MAIN: Looking for %s in: %s", inputName, file)
                if (safeName(inputName) in safeName(file)) or (safeName(fileName) in safeName(inputName)):
                    #pass  # This file does match the Torrent name
                    foundFile = 1
                    Logger.debug("MAIN: Found file %s that matches Torrent Name %s", file, inputName)
                else:
                    continue  # This file does not match the Torrent name, skip it

            if root == 2:
                if foundFile == int(0):
                    Logger.debug("MAIN: Looking for files with modified/created dates less than 5 minutes old.")
                mtime_lapse = now - datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(dirpath, file)))
                ctime_lapse = now - datetime.datetime.fromtimestamp(os.path.getctime(os.path.join(dirpath, file)))
                if (mtime_lapse < datetime.timedelta(minutes=5)) or (ctime_lapse < datetime.timedelta(minutes=5)):
                    #pass  # This file does match the date time criteria
                    foundFile = 1
                    Logger.debug("MAIN: Found file %s with date modifed/created less than 5 minutes ago.", file)
                else:
                    continue  # This file has not been recently moved or created, skip it

            if fileExtension in mediaContainer and is_sample(filePath, inputName, minSampleSize, SampleIDs) and not config()["HeadPhones"].issubsection(inputCategory):   # Ignore samples
                Logger.info("MAIN: Ignoring sample file: %s  ", filePath)
                continue

            if fileExtension in compressedContainer:
                if (config()["SickBeard"].issubsection(inputCategory) and config()["SickBeard"][inputCategory]["nzbExtractionBy"] == "Destination"):
                    # find part numbers in second "extension" from right, if we have more than 1 compressed file in the same directory.
                    if re.search(r'\d+', os.path.splitext(fileName)[1]) and os.path.dirname(filePath) in extracted_folder and not any(item in os.path.splitext(fileName)[1] for item in ['.720p','.1080p','.x264']):
                        part = int(re.search(r'\d+', os.path.splitext(fileName)[1]).group())
                        if part == 1: # we only want to extract the primary part.
                            Logger.debug("MAIN: Found primary part of a multi-part archive %s. Extracting", file)
                        else:
                            Logger.debug("MAIN: Found part %s of a multi-part archive %s. Ignoring", part, file)
                            continue
                    Logger.info("MAIN: Found compressed archive %s for file %s", fileExtension, filePath)
                    try:
                        extractor.extract(filePath, outputDestination)
                        extractionSuccess = True # we use this variable to determine if we need to pause a torrent or not in uTorrent (don't need to pause archived content)
                        extracted_folder.append(os.path.dirname(filePath))
                    except:
                        Logger.exception("MAIN: Extraction failed for: %s", file)
                    continue

            try:
                copy_link(filePath, targetDirectory, useLink, outputDestination)
                copy_list.append([filePath, os.path.join(outputDestination, file)])
            except:
                Logger.exception("MAIN: Failed to link file: %s", file)

    outputDestination = outputDestinationMaster # Reset here.
    if not inputCategory in noFlatten: #don't flatten hp in case multi cd albums, and we need to copy this back later.
        flatten(outputDestination)

    # Now check if video files exist in destination:
    if config()["SickBeard","NzbDrone", "CouchPotato"].issubsection(inputCategory):
        for dirpath, dirnames, filenames in os.walk(outputDestination):
            for file in filenames:
                filePath = os.path.join(dirpath, file)
                fileName, fileExtension = os.path.splitext(file)
                if fileExtension in mediaContainer:  # If the file is a video file
                    Logger.debug("MAIN: Found media file: %s", filePath)
                    video += 1
                if fileExtension in compressedContainer:  # If the file is an archive file
                    archive += 1
        if video > int(0):  # Check that media files exist
            Logger.debug("MAIN: Found %s media files", str(video))
            status = int(0)
        elif not (config()["SickBeard"].issubsection(inputCategory) and config()["SickBeard"][inputCategory]["nzbExtractionBy"] == "Destination") and archive > int(0):
            Logger.debug("MAIN: Found %s archive files to be extracted by SickBeard", str(archive))
            status = int(0)
        else:
            Logger.warning("MAIN: Found no media files in output.")

    if (inputCategory in user_script_categories and not "NONE" in user_script_categories) or ("ALL" in user_script_categories and not inputCategory in processCategories):
        Logger.info("MAIN: Processing user script %s.", user_script)
        result = external_script(outputDestination,inputName,inputCategory)
    elif status == int(0) or (config()['HeadPhones','Mylar','Gamez'].issubsection(inputCategory)): # if movies linked/extracted or for other categories.
        Logger.debug("MAIN: Calling autoProcess script for successful download.")
        status = int(0) # hp, my, gz don't support failed.
    else:
        Logger.error("MAIN: Something failed! Please check logs. Exiting")
        sys.exit(-1)

    result = 0
    if config()['CouchPotato'].issubsection(inputCategory):
        Logger.info("MAIN: Calling CouchPotato:" + inputCategory + " to post-process: %s", inputName)
        download_id = inputHash
        result = autoProcessMovie().process(outputDestination, inputName, status, clientAgent, download_id, inputCategory)
    elif config()['SickBeard'].issubsection(inputCategory):
        Logger.info("MAIN: Calling Sick-Beard:" + inputCategory + " to post-process: %s", inputName)
        result = autoProcessTV().processEpisode(outputDestination, inputName, status, clientAgent, inputCategory)
    elif config()['NzbDrone'].issubsection(inputCategory):
        Logger.info("MAIN: Calling NzbDrone:" + inputCategory + " to post-process: %s", inputName)
        result = autoProcessTV().processEpisode(outputDestination, inputName, status, clientAgent, inputCategory)
    elif config()['HeadPhones'].issubsection(inputCategory):
        Logger.info("MAIN: Calling HeadPhones:" + inputCategory + " to post-process: %s", inputName)
        result = autoProcessMusic().process(inputDirectory, inputName, status, clientAgent, inputCategory)
    elif config()['Mylar'].issubsection(inputCategory):
        Logger.info("MAIN: Calling Mylar:" + inputCategory + " to post-process: %s", inputName)
        result = autoProcessComics().processEpisode(outputDestination, inputName, status, clientAgent, inputCategory)
    elif config()['Gamez'].issubsection(inputCategory):
        Logger.info("MAIN: Calling Gamez:" + inputCategory + " to post-process: %s", inputName)
        result = autoProcessGames().process(outputDestination, inputName, status, clientAgent, inputCategory)

    if result == 1:
        Logger.info("MAIN: A problem was reported in the autoProcess* script. If torrent was paused we will resume seeding")

    resume_torrent(clientAgent, TorrentClass, inputHash, inputID, result, inputName)
    cleanup_output(inputCategory, processCategories, result, outputDestination)
    Logger.info("MAIN: All done.")

def create_torrent_class(clientAgent, inputHash):
    # Hardlink solution for Torrents
    TorrentClass = ""
    if clientAgent in ['utorrent', 'transmission', 'deluge'] and inputHash:
        if clientAgent == 'utorrent':
            try:
                Logger.debug("MAIN: Connecting to %s: %s", clientAgent, uTorrentWEBui)
                TorrentClass = UTorrentClient(uTorrentWEBui, uTorrentUSR, uTorrentPWD)
            except:
                Logger.exception("MAIN: Failed to connect to uTorrent")

        if clientAgent == 'transmission':
            try:
                Logger.debug("MAIN: Connecting to %s: http://%s:%s", clientAgent, TransmissionHost, TransmissionPort)
                TorrentClass = TransmissionClient(TransmissionHost, TransmissionPort, TransmissionUSR, TransmissionPWD)
            except:
                Logger.exception("MAIN: Failed to connect to Transmission")

        if clientAgent == 'deluge':
            try:
                Logger.debug("MAIN: Connecting to %s: http://%s:%s", clientAgent, DelugeHost, DelugePort)
                TorrentClass = DelugeClient()
                TorrentClass.connect(host = DelugeHost, port = DelugePort, username = DelugeUSR, password = DelugePWD)
            except:
                Logger.exception("MAIN: Failed to connect to deluge")

    return TorrentClass

def pause_torrent(clientAgent, TorrentClass, inputHash, inputID, inputName):
    # if we are using links with Torrents it means we need to pause it in order to access the files
    Logger.debug("MAIN: Stoping torrent %s in %s while processing", inputName, clientAgent)
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
        if (int(config()["Torrent"]["deleteOriginal"]) is 1 and result != 1) or useLink == 'move': # if we move files, nothing to resume seeding.
            Logger.debug("MAIN: Deleting torrent %s from %s", inputName, clientAgent)
            if clientAgent == 'utorrent' and TorrentClass != "":
                TorrentClass.removedata(inputHash)
                TorrentClass.remove(inputHash)
            if clientAgent == 'transmission' and TorrentClass !="":
                TorrentClass.remove_torrent(inputID, True)
            if clientAgent == 'deluge' and TorrentClass != "":
                TorrentClass.core.remove_torrent(inputID, True)
        # we always want to resume seeding, for now manually find out what is wrong when extraction fails
        else:
            Logger.debug("MAIN: Starting torrent %s in %s", inputName, clientAgent)
            if clientAgent == 'utorrent' and TorrentClass != "":
                TorrentClass.start(inputHash)
            if clientAgent == 'transmission' and TorrentClass !="":
                TorrentClass.start_torrent(inputID)
            if clientAgent == 'deluge' and TorrentClass != "":
                TorrentClass.core.resume_torrent([inputID])
        time.sleep(5)

def cleanup_output(inputCategory, processCategories, result, outputDestination): 
    if inputCategory in processCategories and result == 0 and os.path.isdir(outputDestination):
        num_files_new = int(0)
        file_list = []
        for dirpath, dirnames, filenames in os.walk(outputDestination):
            for file in filenames:
                filePath = os.path.join(dirpath, file)
                fileName, fileExtension = os.path.splitext(file)
                if fileExtension in mediaContainer or fileExtension in metaContainer:
                    num_files_new += 1
                    file_list.append(file)
        if num_files_new is 0 or int(config()["Torrent"]["forceClean"]) is 1:
            Logger.info("All files have been processed. Cleaning outputDirectory %s", outputDestination)
            shutil.rmtree(outputDestination)
        else:
            Logger.info("outputDirectory %s still contains %s media and/or meta files. This directory will not be removed.", outputDestination, num_files_new)
            for item in file_list:
                Logger.debug("media/meta file found: %s", item)

def external_script(outputDestination, torrentName, torrentLabel):

    final_result = int(0) # start at 0.
    num_files = int(0)
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:

            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in user_script_mediaExtensions or "ALL" in user_script_mediaExtensions:
                num_files = num_files + 1
                if user_script_runOnce == 1 and num_files > 1: # we have already run once, so just continue to get number of files.
                    continue
                command = [user_script]
                for param in user_script_param:
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
                        if user_script_runOnce == 1:
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
                Logger.info("Running script %s on file %s.", cmd, filePath)
                try:
                    p = Popen(command)
                    res = p.wait()
                    if str(res) in user_script_successCodes: # Linux returns 0 for successful.
                        Logger.info("UserScript %s was successfull", command[0])
                        result = int(0)
                    else:
                        Logger.error("UserScript %s has failed with return code: %s", command[0], res)
                        Logger.info("If the UserScript completed successfully you should add %s to the user_script_successCodes", res)
                        result = int(1)
                except:
                    Logger.exception("UserScript %s has failed", command[0])
                    result = int(1)
                final_result = final_result + result

    time.sleep(user_delay)
    num_files_new = int(0)
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in user_script_mediaExtensions or user_script_mediaExtensions == "ALL":
                num_files_new = num_files_new + 1

    if user_script_clean == int(1) and num_files_new == int(0) and final_result == int(0):
        Logger.info("All files have been processed. Cleaning outputDirectory %s", outputDestination)
        shutil.rmtree(outputDestination)
    elif user_script_clean == int(1) and num_files_new != int(0):
        Logger.info("%s files were processed, but %s still remain. outputDirectory will not be cleaned.", num_files, num_files_new)
    return final_result

if __name__ == "__main__":
    # run migrate to convert old cfg to new style cfg plus fix any cfg missing values/options.
    if config().migrate():
        nzbtomedia_configure_logging(config.LOG_FILE)
        Logger = logging.getLogger(__name__)
        Logger.info("====================")  # Seperate old from new log
        Logger.info("TorrentToMedia %s", config.NZBTOMEDIA_VERSION)

        Logger.info("MAIN: Loading config from %s", config.CONFIG_FILE)
    else:
        sys.exit(-1)

    WakeUp()

    # EXAMPLE VALUES:
    clientAgent = config()["Torrent"]["clientAgent"]                                  # utorrent | deluge | transmission | rtorrent | other
    useLink = config()["Torrent"]["useLink"]                                          # no | hard | sym
    outputDirectory = config()["Torrent"]["outputDirectory"]                          # /abs/path/to/complete/
    categories = (config()["Torrent"]["categories"])                                  # music,music_videos,pictures,software
    noFlatten = (config()["Torrent"]["noFlatten"])

    uTorrentWEBui = config()["Torrent"]["uTorrentWEBui"]                              # http://localhost:8090/gui/
    uTorrentUSR = config()["Torrent"]["uTorrentUSR"]                                  # mysecretusr
    uTorrentPWD = config()["Torrent"]["uTorrentPWD"]                                  # mysecretpwr

    TransmissionHost = config()["Torrent"]["TransmissionHost"]                        # localhost
    TransmissionPort = config()["Torrent"]["TransmissionPort"]                        # 8084
    TransmissionUSR = config()["Torrent"]["TransmissionUSR"]                          # mysecretusr
    TransmissionPWD = config()["Torrent"]["TransmissionPWD"]                          # mysecretpwr

    DelugeHost = config()["Torrent"]["DelugeHost"]                                    # localhost
    DelugePort = config()["Torrent"]["DelugePort"]                                    # 8084
    DelugeUSR = config()["Torrent"]["DelugeUSR"]                                      # mysecretusr
    DelugePWD = config()["Torrent"]["DelugePWD"]                                      # mysecretpwr

    compressedContainer = (config()["Extensions"]["compressedExtensions"])            # .zip,.rar,.7z
    mediaContainer = (config()["Extensions"]["mediaExtensions"])                      # .mkv,.avi,.divx
    metaContainer = (config()["Extensions"]["metaExtensions"])                        # .nfo,.sub,.srt
    minSampleSize = int(config()["Extensions"]["minSampleSize"])                      # 200 (in MB)
    SampleIDs = (config()["Extensions"]["SampleIDs"])                                 # sample,-s.

    sections = ("CouchPotato", "SickBeard", "NzbDrone", "HeadPhones", "Mylar", "Gamez")
    subsections = config()[sections].subsections
    categories += config()[sections].sections

    user_script_categories = config()["UserScript"]["user_script_categories"]         # NONE
    if not "NONE" in user_script_categories:
        user_script_mediaExtensions = (config()["UserScript"]["user_script_mediaExtensions"])
        user_script = config()["UserScript"]["user_script_path"]
        user_script_param = (config()["UserScript"]["user_script_param"])
        user_script_successCodes = (config()["UserScript"]["user_script_successCodes"])
        user_script_clean = int(config()["UserScript"]["user_script_clean"])
        user_delay = int(config()["UserScript"]["delay"])
        user_script_runOnce = int(config()["UserScript"]["user_script_runOnce"])

    transcode = int(config()["Transcoder"]["transcode"])

    n = 0
    for arg in sys.argv:
        Logger.debug("arg %s is: %s", n, arg)
        n = n+1

    try:
        inputDirectory, inputName, inputCategory, inputHash, inputID = parse_args(clientAgent)
    except:
        Logger.exception("MAIN: There was a problem loading variables")
        sys.exit(-1)

        # check if this is a manual run
    if inputDirectory is None:
        for section, subsection in subsections.items():
            for category in subsection:
                if config()[section].isenabled(category):
                    dirNames = get_dirnames(section, category)
                    for dirName in dirNames:
                        Logger.info("MAIN: TorrentToMedia running %s:%s as a manual run for folder %s ...", section, category, dirName)
                        main(dirName, os.path.basename(dirName), category, inputHash, inputID)
                else:
                    Logger.info("MAIN: nzbTo%s %s:%s is DISABLED, you can enable this in autoProcessMedia.cfg ...",section, section, category)
    else:
        main(inputDirectory, inputName, inputCategory, inputHash, inputID)
