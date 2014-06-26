#!/usr/bin/env python2
import datetime
import os
import time
import shutil
import sys
import nzbtomedia

from subprocess import Popen
from nzbtomedia import logger, nzbToMediaDB
from nzbtomedia.nzbToMediaUtil import convert_to_ascii, CharReplace

def processTorrent(inputDirectory, inputName, inputCategory, inputHash, inputID, clientAgent):
    status = 1  # 1 = failed | 0 = success
    root = 0
    foundFile = 0
    uniquePath = 1

    if clientAgent != 'manual' and not nzbtomedia.DOWNLOADINFO:
        logger.debug('Adding TORRENT download info for directory %s to database' % (inputDirectory))

        myDB = nzbToMediaDB.DBConnection()

        encoded, inputDirectory1 = CharReplace(inputDirectory)
        encoded, inputName1 = CharReplace(inputName)

        controlValueDict = {"input_directory": unicode(inputDirectory1)}
        newValueDict = {"input_name": unicode(inputName1),
                        "input_hash": unicode(inputHash),
                        "input_id": unicode(inputID),
                        "client_agent": unicode(clientAgent),
                        "status": 0,
                        "last_update": datetime.date.today().toordinal()
        }
        myDB.upsert("downloads", newValueDict, controlValueDict)

    logger.debug("Received Directory: %s | Name: %s | Category: %s" % (inputDirectory, inputName, inputCategory))

    inputDirectory, inputName, inputCategory, root = nzbtomedia.category_search(inputDirectory, inputName,
                                                                                        inputCategory, root,
                                                                                        nzbtomedia.CATEGORIES)  # Confirm the category by parsing directory structure

    if inputCategory == "":
        inputCategory = "UNCAT"

    usercat = inputCategory

    logger.debug("Determined Directory: %s | Name: %s | Category: %s" % (inputDirectory, inputName, inputCategory))

    # auto-detect section
    section = nzbtomedia.CFG.findsection(inputCategory).isenabled()
    if section is None:
        section = nzbtomedia.CFG.findsection("ALL").isenabled()
        if section is None:
            logger.error(
                'Category:[%s] is not defined or is not enabled. Please rename it or ensure it is enabled for the appropriate section in your autoProcessMedia.cfg and try again.' % (
                    inputCategory))
            return -1
        else:
            usercat = "ALL"

    if len(section) > 1:
        logger.error(
            'Category:[%s] is not unique, %s are using it. Please rename it or disable all other sections using the same category name in your autoProcessMedia.cfg and try again.' % (
                usercat, section.keys()))
        return -1

    if section:
        sectionName = section.keys()[0]
        logger.info('Auto-detected SECTION:%s' % (sectionName))
    else:
        logger.error("Unable to locate a section with subsection:%s enabled in your autoProcessMedia.cfg, exiting!" % (
            inputCategory))
        return -1

    try:
        Torrent_NoLink = int(section[usercat]["Torrent_NoLink"])
    except:
        Torrent_NoLink = 0

    try:
        extract = int(section[usercat]['extract'])
    except:
        extract = 0

    if sectionName == "UserScript":
        try:
            nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS = section[usercat]["user_script_mediaExtensions"]
        except:
            nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS = None
        try:
            nzbtomedia.USER_SCRIPT = section[usercat]["user_script_path"]
        except:
            nzbtomedia.USER_SCRIPT = None
        try:
            nzbtomedia.USER_SCRIPT_PARAM = section[usercat]["user_script_param"]
        except:
            nzbtomedia.USER_SCRIPT_PARAM = None
        try:
            nzbtomedia.USER_SCRIPT_SUCCESSCODES = section[usercat]["user_script_successCodes"]
        except:
            nzbtomedia.USER_SCRIPT_SUCCESSCODES = 0
        try:
            nzbtomedia.USER_SCRIPT_CLEAN = int(section[usercat]["user_script_clean"])
        except:
            nzbtomedia.USER_SCRIPT_CLEAN = 1
        try:
            nzbtomedia.USER_SCRIPT_RUNONCE = int(section[usercat]["user_script_runOnce"])
        except:
            nzbtomedia.USER_SCRIPT_RUNONCE = 1
        try:
            uniquePath = int(section[usercat]["unique_path"])
        except:
            uniquePath = 1

    if clientAgent != 'manual':
        nzbtomedia.pause_torrent(clientAgent, inputHash, inputID, inputName)

    if uniquePath:
        outputDestination = os.path.normpath(
            nzbtomedia.os.path.join(nzbtomedia.OUTPUTDIRECTORY, inputCategory, nzbtomedia.sanitizeName(inputName)))
    else:
        outputDestination = os.path.normpath(
            nzbtomedia.os.path.join(nzbtomedia.OUTPUTDIRECTORY, inputCategory))

    logger.info("Output directory set to: %s" % (outputDestination))

    if nzbtomedia.SAFE_MODE and outputDestination == nzbtomedia.TORRENT_DEFAULTDIR:
        logger.error(
            'The output directory:[%s] is the Download Directory. Edit outputDirectory in autoProcessMedia.cfg. Exiting' % (
            inputDirectory))
        return -1

    logger.debug("Scanning files in directory: %s" % (inputDirectory))

    if sectionName == 'HeadPhones':
        nzbtomedia.NOFLATTEN.extend(
            inputCategory)  # Make sure we preserve folder structure for HeadPhones.

    now = datetime.datetime.now()

    inputFiles = nzbtomedia.listMediaFiles(inputDirectory)
    logger.debug("Found %s files in %s" % (str(len(inputFiles)), inputDirectory))
    for inputFile in inputFiles:
        filePath = os.path.dirname(inputFile)
        fileName, fileExt = os.path.splitext(os.path.basename(inputFile))
        fullFileName = os.path.basename(inputFile)

        targetFile = nzbtomedia.os.path.join(outputDestination, fullFileName)
        if inputCategory in nzbtomedia.NOFLATTEN:
            if not os.path.basename(filePath) in outputDestination:
                targetFile = nzbtomedia.os.path.join(
                    nzbtomedia.os.path.join(outputDestination, os.path.basename(filePath)), fullFileName)
                logger.debug(
                    "Setting outputDestination to %s to preserve folder structure" % (os.path.dirname(targetFile)))

        if root == 1:
            if not foundFile:
                logger.debug("Looking for %s in: %s" % (inputName, inputFile))
            if (nzbtomedia.sanitizeName(inputName) in nzbtomedia.sanitizeName(inputFile)) or (
                        nzbtomedia.sanitizeName(fileName) in nzbtomedia.sanitizeName(inputName)):
                foundFile = True
                logger.debug("Found file %s that matches Torrent Name %s" % (fullFileName, inputName))
            else:
                continue

        if root == 2:
            mtime_lapse = now - datetime.datetime.fromtimestamp(os.path.getmtime(inputFile))
            ctime_lapse = now - datetime.datetime.fromtimestamp(os.path.getctime(inputFile))

            if not foundFile:
                logger.debug("Looking for files with modified/created dates less than 5 minutes old.")
            if (mtime_lapse < datetime.timedelta(minutes=5)) or (ctime_lapse < datetime.timedelta(minutes=5)):
                foundFile = True
                logger.debug("Found file %s with date modifed/created less than 5 minutes ago." % (fullFileName))
            else:
                continue  # This file has not been recently moved or created, skip it

        if Torrent_NoLink == 0:
            try:
                nzbtomedia.copy_link(inputFile, targetFile, nzbtomedia.USELINK)
                nzbtomedia.rmReadOnly(targetFile)
            except:
                logger.error("Failed to link: %s to %s" % (inputFile, targetFile))

    if not inputCategory in nzbtomedia.NOFLATTEN:  #don't flatten hp in case multi cd albums, and we need to copy this back later.
        nzbtomedia.flatten(outputDestination)

    inputName, outputDestination = convert_to_ascii(inputName, outputDestination)

    if extract == 1:
        logger.debug('Checking for archives to extract in directory: %s' % (outputDestination))
        nzbtomedia.extractFiles(outputDestination)

    # Now check if video files exist in destination:
    if sectionName in ["SickBeard", "NzbDrone", "CouchPotato"]:
        numVideos = len(
            nzbtomedia.listMediaFiles(outputDestination, media=True, audio=False, meta=False, archives=False))
        if numVideos > 0:
            logger.info("Found %s media files in %s" % (numVideos, outputDestination))
            status = 0
        elif extract != 1:
            logger.info("Found no media files in %s. Sending to %s to process" % (outputDestination, sectionName))
            status = 0
        else:
            logger.warning("Found no media files in %s" % outputDestination)

    # Only these sections can handling failed downloads so make sure everything else gets through without the check for failed
    if not sectionName in ['CouchPotato', 'SickBeard', 'NzbDrone']:
        status = 0

    logger.info("Calling %s:%s to post-process:%s" % (sectionName, usercat, inputName))

    result = 0
    if sectionName == 'UserScript':
        result = external_script(outputDestination, inputName, inputCategory)

    if sectionName == 'CouchPotato':
        result = nzbtomedia.autoProcessMovie().process(sectionName,outputDestination, inputName, status, clientAgent, inputHash,
                                                       inputCategory)
    elif sectionName in ['SickBeard','NzbDrone']:
        result = nzbtomedia.autoProcessTV().processEpisode(sectionName,outputDestination, inputName, status, clientAgent,
                                                           inputCategory)
    elif sectionName == 'HeadPhones':
        result = nzbtomedia.autoProcessMusic().process(sectionName,outputDestination, inputName, status, clientAgent, inputCategory)
    elif sectionName == 'Mylar':
        result = nzbtomedia.autoProcessComics().processEpisode(sectionName,outputDestination, inputName, status, clientAgent,
                                                               inputCategory)
    elif sectionName == 'Gamez':
        result = nzbtomedia.autoProcessGames().process(sectionName,outputDestination, inputName, status, clientAgent, inputCategory)

    if result != 0:
        if clientAgent != 'manual':
            logger.error(
                "A problem was reported in the autoProcess* script. If torrent was paused we will resume seeding")
            nzbtomedia.resume_torrent(clientAgent, inputHash, inputID, inputName)
    else:
        if clientAgent != 'manual':
            # update download status in our DB
            nzbtomedia.update_downloadInfoStatus(inputName, 1)

            # remove torrent
            nzbtomedia.remove_torrent(clientAgent, inputHash, inputID, inputName)

        if not sectionName == 'UserScript':  # for user script, we assume this is cleaned by the script or option USER_SCRIPT_CLEAN
            # cleanup our processing folders of any misc unwanted files and empty directories
            nzbtomedia.cleanDir(outputDestination, sectionName, inputCategory)

    return result


def external_script(outputDestination, torrentName, torrentLabel):
    if nzbtomedia.USER_SCRIPT is None or nzbtomedia.USER_SCRIPT == "None":  # do nothing and return success.
        return 0
    final_result = 0  # start at 0.
    num_files = 0
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:

            filePath = nzbtomedia.os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS or "ALL" in nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS:
                num_files = num_files + 1
                if nzbtomedia.USER_SCRIPT_RUNONCE == 1 and num_files > 1:  # we have already run once, so just continue to get number of files.
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
                    if str(res) in nzbtomedia.USER_SCRIPT_SUCCESSCODES:  # Linux returns 0 for successful.
                        logger.info("UserScript %s was successfull" % (command[0]))
                        result = 0
                    else:
                        logger.error("UserScript %s has failed with return code: %s" % (command[0], res))
                        logger.info(
                            "If the UserScript completed successfully you should add %s to the user_script_successCodes" % (
                                res))
                        result = int(1)
                except:
                    logger.error("UserScript %s has failed" % (command[0]))
                    result = int(1)
                final_result = final_result + result

    num_files_new = 0
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:
            filePath = nzbtomedia.os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS or nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS == "ALL":
                num_files_new = num_files_new + 1

    if nzbtomedia.USER_SCRIPT_CLEAN == int(1) and num_files_new == 0 and final_result == 0:
        logger.info("All files have been processed. Cleaning outputDirectory %s" % (outputDestination))
        shutil.rmtree(outputDestination)
    elif nzbtomedia.USER_SCRIPT_CLEAN == int(1) and num_files_new != 0:
        logger.info("%s files were processed, but %s still remain. outputDirectory will not be cleaned." % (
            num_files, num_files_new))
    return final_result


def main(args):
    # Initialize the config
    nzbtomedia.initialize()

    # clientAgent for Torrents
    clientAgent = nzbtomedia.TORRENT_CLIENTAGENT

    logger.info("#########################################################")
    logger.info("## ..::[%s]::.. ##" % os.path.basename(__file__))
    logger.info("#########################################################")

    # debug command line options
    logger.debug("Options passed into TorrentToMedia: %s" % (args))

    # Post-Processing Result
    result = 0

    try:
        inputDirectory, inputName, inputCategory, inputHash, inputID = nzbtomedia.parse_args(clientAgent, args)
    except:
        logger.error("There was a problem loading variables")
        return -1

    if inputDirectory and inputName and inputHash and inputID:
        result = processTorrent(inputDirectory, inputName, inputCategory, inputHash, inputID, clientAgent)
    else:
        # Perform Manual Post-Processing
        logger.warning("Invalid number of arguments received from client, Switching to manual run mode ...")

        for section, subsections in nzbtomedia.SECTIONS.items():
            for subsection in subsections:
                for dirName in nzbtomedia.getDirs(section,subsection):
                    logger.info("Starting manual run for %s:%s - Folder:%s" % (section, subsection, dirName))

                    logger.info("Checking database for download info for %s ..." % (os.path.basename(dirName)))
                    nzbtomedia.DOWNLOADINFO = nzbtomedia.get_downloadInfo(os.path.basename(dirName), 0)
                    if nzbtomedia.DOWNLOADINFO:
                        logger.info(
                            "Found download info for %s, setting variables now ..." % (os.path.basename(dirName)))
                    else:
                        logger.info(
                            'Unable to locate download info for %s, continuing to try and process this release ...' % (
                                os.path.basename(dirName))
                        )

                    try:
                        clientAgent = str(nzbtomedia.DOWNLOADINFO[0]['client_agent'])
                    except:
                        clientAgent = 'manual'
                    try:
                        inputHash = str(nzbtomedia.DOWNLOADINFO[0]['input_hash'])
                    except:
                        inputHash = None
                    try:
                        inputID = str(nzbtomedia.DOWNLOADINFO[0]['input_id'])
                    except:
                        inputID = None

                    if clientAgent.lower() not in nzbtomedia.TORRENT_CLIENTS and clientAgent != 'manual':
                        continue

                    results = processTorrent(dirName, os.path.basename(dirName), subsection, inputHash, inputID,
                                             clientAgent)
                    if results != 0:
                        logger.error("A problem was reported when trying to perform a manual run for %s:%s." % (
                            section, subsection))
                        result = results

    if result == 0:
        logger.info("The %s script completed successfully." % (args[0]))
    else:
        logger.error("A problem was reported in the %s script." % (args[0]))

    return result


if __name__ == "__main__":
    exit(main(sys.argv))
