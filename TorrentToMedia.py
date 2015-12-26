#!/usr/bin/env python2
import datetime
import os
import time
import shutil
import sys
import core

from subprocess import Popen
from core import logger, nzbToMediaDB
from core.nzbToMediaUtil import convert_to_ascii, CharReplace, plex_update
from core.nzbToMediaUserScript import external_script

def processTorrent(inputDirectory, inputName, inputCategory, inputHash, inputID, clientAgent):
    status = 1  # 1 = failed | 0 = success
    root = 0
    foundFile = 0
    uniquePath = 1

    if clientAgent != 'manual' and not core.DOWNLOADINFO:
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

    inputDirectory, inputName, inputCategory, root = core.category_search(inputDirectory, inputName,
                                                                                        inputCategory, root,
                                                                                        core.CATEGORIES)  # Confirm the category by parsing directory structure 
    if inputCategory == "":
        inputCategory = "UNCAT"

    usercat = inputCategory
    try:
        inputName = inputName.encode(core.SYS_ENCODING)
    except: pass
    try:
        inputDirectory = inputDirectory.encode(core.SYS_ENCODING)
    except: pass

    logger.debug("Determined Directory: %s | Name: %s | Category: %s" % (inputDirectory, inputName, inputCategory))

    # auto-detect section
    section = core.CFG.findsection(inputCategory).isenabled()
    if section is None:
        section = core.CFG.findsection("ALL").isenabled()
        if section is None:
            logger.error(
                'Category:[%s] is not defined or is not enabled. Please rename it or ensure it is enabled for the appropriate section in your autoProcessMedia.cfg and try again.' % (
                    inputCategory))
            return [-1, ""]
        else:
            usercat = "ALL"

    if len(section) > 1:
        logger.error(
            'Category:[%s] is not unique, %s are using it. Please rename it or disable all other sections using the same category name in your autoProcessMedia.cfg and try again.' % (
                usercat, section.keys()))
        return [-1, ""]

    if section:
        sectionName = section.keys()[0]
        logger.info('Auto-detected SECTION:%s' % (sectionName))
    else:
        logger.error("Unable to locate a section with subsection:%s enabled in your autoProcessMedia.cfg, exiting!" % (
            inputCategory))
        return [-1, ""]

    try:
        Torrent_NoLink = int(section[usercat]["Torrent_NoLink"])
    except:
        Torrent_NoLink = 0

    try:
        keep_archive = int(section[usercat]["keep_archive"])
    except:
        keep_archive = 0

    try:
        extract = int(section[usercat]['extract'])
    except:
        extract = 0

    try:
        uniquePath = int(section[usercat]["unique_path"])
    except:
        uniquePath = 1

    if clientAgent != 'manual':
        core.pause_torrent(clientAgent, inputHash, inputID, inputName)

    # Incase input is not directory, make sure to create one.
    # This way Processing is isolated.
    if not os.path.isdir(os.path.join(inputDirectory, inputName)):
        basename = os.path.splitext(core.sanitizeName(inputName))[0]
        outputDestination = os.path.join(core.OUTPUTDIRECTORY, inputCategory, basename)
    elif uniquePath:
        outputDestination = os.path.normpath(
            core.os.path.join(core.OUTPUTDIRECTORY, inputCategory, core.sanitizeName(inputName)))
    else:
        outputDestination = os.path.normpath(
            core.os.path.join(core.OUTPUTDIRECTORY, inputCategory))
    try:
        outputDestination = outputDestination.encode(core.SYS_ENCODING)
    except: pass

    if outputDestination in inputDirectory:
        outputDestination = inputDirectory

    logger.info("Output directory set to: %s" % (outputDestination))

    if core.SAFE_MODE and outputDestination == core.TORRENT_DEFAULTDIR:
        logger.error(
            'The output directory:[%s] is the Download Directory. Edit outputDirectory in autoProcessMedia.cfg. Exiting' % (
            inputDirectory))
        return [-1, ""]

    logger.debug("Scanning files in directory: %s" % (inputDirectory))

    if sectionName == 'HeadPhones':
        core.NOFLATTEN.extend(
            inputCategory)  # Make sure we preserve folder structure for HeadPhones.

    now = datetime.datetime.now()

    inputFiles = core.listMediaFiles(inputDirectory)
    logger.debug("Found %s files in %s" % (str(len(inputFiles)), inputDirectory))
    for inputFile in inputFiles:
        filePath = os.path.dirname(inputFile)
        fileName, fileExt = os.path.splitext(os.path.basename(inputFile))
        fullFileName = os.path.basename(inputFile)

        targetFile = core.os.path.join(outputDestination, fullFileName)
        if inputCategory in core.NOFLATTEN:
            if not os.path.basename(filePath) in outputDestination:
                targetFile = core.os.path.join(
                    core.os.path.join(outputDestination, os.path.basename(filePath)), fullFileName)
                logger.debug(
                    "Setting outputDestination to %s to preserve folder structure" % (os.path.dirname(targetFile)))
        try:
            targetFile = targetFile.encode(core.SYS_ENCODING)
        except: pass
        if root == 1:
            if not foundFile:
                logger.debug("Looking for %s in: %s" % (inputName, inputFile))
            if (core.sanitizeName(inputName) in core.sanitizeName(inputFile)) or (
                        core.sanitizeName(fileName) in core.sanitizeName(inputName)):
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
                core.copy_link(inputFile, targetFile, core.USELINK)
                core.rmReadOnly(targetFile)
            except:
                logger.error("Failed to link: %s to %s" % (inputFile, targetFile))

    inputName, outputDestination = convert_to_ascii(inputName, outputDestination)

    if extract == 1:
        logger.debug('Checking for archives to extract in directory: %s' % (outputDestination))
        core.extractFiles(inputDirectory, outputDestination, keep_archive)

    if not inputCategory in core.NOFLATTEN:  #don't flatten hp in case multi cd albums, and we need to copy this back later.
        core.flatten(outputDestination)

    # Now check if video files exist in destination:
    if sectionName in ["SickBeard", "NzbDrone", "CouchPotato"]:
        numVideos = len(
            core.listMediaFiles(outputDestination, media=True, audio=False, meta=False, archives=False))
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

    if core.TORRENT_CHMOD_DIRECTORY:
        core.rchmod(outputDestination, core.TORRENT_CHMOD_DIRECTORY)

    result = [ 0, "" ]
    if sectionName == 'UserScript':
        result = external_script(outputDestination, inputName, inputCategory, section[usercat])

    elif sectionName == 'CouchPotato':
        result = core.autoProcessMovie().process(sectionName,outputDestination, inputName, status, clientAgent, inputHash,
                                                       inputCategory)
    elif sectionName in ['SickBeard','NzbDrone']:
        if inputHash:
            inputHash = inputHash.upper()
        result = core.autoProcessTV().processEpisode(sectionName,outputDestination, inputName, status, clientAgent,
                                                           inputHash, inputCategory)
    elif sectionName == 'HeadPhones':
        result = core.autoProcessMusic().process(sectionName,outputDestination, inputName, status, clientAgent, inputCategory)
    elif sectionName == 'Mylar':
        result = core.autoProcessComics().processEpisode(sectionName,outputDestination, inputName, status, clientAgent,
                                                               inputCategory)
    elif sectionName == 'Gamez':
        result = core.autoProcessGames().process(sectionName,outputDestination, inputName, status, clientAgent, inputCategory)

    plex_update(inputCategory)

    if result[0] != 0:
        if not core.TORRENT_RESUME_ON_FAILURE:
            logger.error("A problem was reported in the autoProcess* script. torrent won't resume seeding (settings)")
        elif clientAgent != 'manual':
            logger.error(
                "A problem was reported in the autoProcess* script. If torrent was paused we will resume seeding")
            core.resume_torrent(clientAgent, inputHash, inputID, inputName)

    else:
        if clientAgent != 'manual':
            # update download status in our DB
            core.update_downloadInfoStatus(inputName, 1)

            # remove torrent
            if core.USELINK == 'move-sym' and not core.DELETE_ORIGINAL == 1:
                logger.debug('Checking for sym-links to re-direct in: %s' % (inputDirectory))
                for dirpath, dirs, files in os.walk(inputDirectory):
                    for file in files:
                        logger.debug('Checking symlink: %s' % (os.path.join(dirpath,file)))
                        core.replace_links(os.path.join(dirpath,file))
            core.remove_torrent(clientAgent, inputHash, inputID, inputName)

        if not sectionName == 'UserScript':  # for user script, we assume this is cleaned by the script or option USER_SCRIPT_CLEAN
            # cleanup our processing folders of any misc unwanted files and empty directories
            core.cleanDir(outputDestination, sectionName, inputCategory)

    return result


def main(args):
    # Initialize the config
    core.initialize()

    # clientAgent for Torrents
    clientAgent = core.TORRENT_CLIENTAGENT

    logger.info("#########################################################")
    logger.info("## ..::[%s]::.. ##" % os.path.basename(__file__))
    logger.info("#########################################################")

    # debug command line options
    logger.debug("Options passed into TorrentToMedia: %s" % (args))

    # Post-Processing Result
    result = [ 0, "" ]

    try:
        inputDirectory, inputName, inputCategory, inputHash, inputID = core.parse_args(clientAgent, args)
    except:
        logger.error("There was a problem loading variables")
        return -1

    if inputDirectory and inputName and inputHash and inputID:
        result = processTorrent(inputDirectory, inputName, inputCategory, inputHash, inputID, clientAgent)
    else:
        # Perform Manual Post-Processing
        logger.warning("Invalid number of arguments received from client, Switching to manual run mode ...")

        for section, subsections in core.SECTIONS.items():
            for subsection in subsections:
                if not core.CFG[section][subsection].isenabled():
                    continue
                for dirName in core.getDirs(section, subsection, link='hard'):
                    logger.info("Starting manual run for %s:%s - Folder:%s" % (section, subsection, dirName))

                    logger.info("Checking database for download info for %s ..." % (os.path.basename(dirName)))
                    core.DOWNLOADINFO = core.get_downloadInfo(os.path.basename(dirName), 0)
                    if core.DOWNLOADINFO:
                        logger.info(
                            "Found download info for %s, setting variables now ..." % (os.path.basename(dirName)))
                    else:
                        logger.info(
                            'Unable to locate download info for %s, continuing to try and process this release ...' % (
                                os.path.basename(dirName))
                        )

                    try:
                        clientAgent = str(core.DOWNLOADINFO[0]['client_agent'])
                    except:
                        clientAgent = 'manual'
                    try:
                        inputHash = str(core.DOWNLOADINFO[0]['input_hash'])
                    except:
                        inputHash = None
                    try:
                        inputID = str(core.DOWNLOADINFO[0]['input_id'])
                    except:
                        inputID = None

                    if clientAgent.lower() not in core.TORRENT_CLIENTS and clientAgent != 'manual':
                        continue

                    try:
                        dirName = dirName.encode(core.SYS_ENCODING)
                    except: pass
                    inputName = os.path.basename(dirName)
                    try:
                        inputName = inputName.encode(core.SYS_ENCODING)
                    except: pass

                    results = processTorrent(dirName, inputName, subsection, inputHash, inputID,
                                             clientAgent)
                    if results[0] != 0:
                        logger.error("A problem was reported when trying to perform a manual run for %s:%s." % (
                            section, subsection))
                        result = results

    if result[0] == 0:
        logger.info("The %s script completed successfully." % (args[0]))
    else:
        logger.error("A problem was reported in the %s script." % (args[0]))
    del core.MYAPP
    return result[0]


if __name__ == "__main__":
    exit(main(sys.argv))
