#!/usr/bin/env python2
# coding=utf-8
import datetime
import os
import sys
import core

from libs.six import text_type
from core import logger, nzbToMediaDB
from core.nzbToMediaUtil import convert_to_ascii, CharReplace, plex_update, replace_links
from core.nzbToMediaUserScript import external_script


def processTorrent(inputDirectory, inputName, inputCategory, inputHash, inputID, clientAgent):
    status = 1  # 1 = failed | 0 = success
    root = 0
    foundFile = 0

    if clientAgent != 'manual' and not core.DOWNLOADINFO:
        logger.debug('Adding TORRENT download info for directory {0} to database'.format(inputDirectory))

        myDB = nzbToMediaDB.DBConnection()

        inputDirectory1 = inputDirectory
        inputName1 = inputName

        try:
            encoded, inputDirectory1 = CharReplace(inputDirectory)
            encoded, inputName1 = CharReplace(inputName)
        except:
            pass

        controlValueDict = {"input_directory": text_type(inputDirectory1)}
        newValueDict = {"input_name": text_type(inputName1),
                        "input_hash": text_type(inputHash),
                        "input_id": text_type(inputID),
                        "client_agent": text_type(clientAgent),
                        "status": 0,
                        "last_update": datetime.date.today().toordinal()
                        }
        myDB.upsert("downloads", newValueDict, controlValueDict)

    logger.debug("Received Directory: {0} | Name: {1} | Category: {2}".format(inputDirectory, inputName, inputCategory))

    # Confirm the category by parsing directory structure
    inputDirectory, inputName, inputCategory, root = core.category_search(inputDirectory, inputName, inputCategory,
                                                                          root, core.CATEGORIES)
    if inputCategory == "":
        inputCategory = "UNCAT"

    usercat = inputCategory
    try:
        inputName = inputName.encode(core.SYS_ENCODING)
    except UnicodeError:
        pass
    try:
        inputDirectory = inputDirectory.encode(core.SYS_ENCODING)
    except UnicodeError:
        pass

    logger.debug("Determined Directory: {0} | Name: {1} | Category: {2}".format
                 (inputDirectory, inputName, inputCategory))

    # auto-detect section
    section = core.CFG.findsection(inputCategory).isenabled()
    if section is None:
        section = core.CFG.findsection("ALL").isenabled()
        if section is None:
            logger.error('Category:[{0}] is not defined or is not enabled. '
                         'Please rename it or ensure it is enabled for the appropriate section '
                         'in your autoProcessMedia.cfg and try again.'.format
                         (inputCategory))
            return [-1, ""]
        else:
            usercat = "ALL"

    if len(section) > 1:
        logger.error('Category:[{0}] is not unique, {1} are using it. '
                     'Please rename it or disable all other sections using the same category name '
                     'in your autoProcessMedia.cfg and try again.'.format
                     (usercat, section.keys()))
        return [-1, ""]

    if section:
        sectionName = section.keys()[0]
        logger.info('Auto-detected SECTION:{0}'.format(sectionName))
    else:
        logger.error("Unable to locate a section with subsection:{0} "
                     "enabled in your autoProcessMedia.cfg, exiting!".format
                     (inputCategory))
        return [-1, ""]

    section = dict(section[sectionName][usercat])  # Type cast to dict() to allow effective usage of .get()

    Torrent_NoLink = int(section.get("Torrent_NoLink", 0))
    keep_archive = int(section.get("keep_archive", 0))
    extract = int(section.get('extract', 0))
    extensions = section.get('user_script_mediaExtensions', "").lower().split(',')
    uniquePath = int(section.get("unique_path", 1))

    if clientAgent != 'manual':
        core.pause_torrent(clientAgent, inputHash, inputID, inputName)

    # In case input is not directory, make sure to create one.
    # This way Processing is isolated.
    if not os.path.isdir(os.path.join(inputDirectory, inputName)):
        basename = os.path.basename(inputDirectory)
        basename = core.sanitizeName(inputName) \
            if inputName == basename else os.path.splitext(core.sanitizeName(inputName))[0]
        outputDestination = os.path.join(core.OUTPUTDIRECTORY, inputCategory, basename)
    elif uniquePath:
        outputDestination = os.path.normpath(
            core.os.path.join(core.OUTPUTDIRECTORY, inputCategory, core.sanitizeName(inputName).replace(" ",".")))
    else:
        outputDestination = os.path.normpath(
            core.os.path.join(core.OUTPUTDIRECTORY, inputCategory))
    try:
        outputDestination = outputDestination.encode(core.SYS_ENCODING)
    except UnicodeError:
        pass

    if outputDestination in inputDirectory:
        outputDestination = inputDirectory

    logger.info("Output directory set to: {0}".format(outputDestination))

    if core.SAFE_MODE and outputDestination == core.TORRENT_DEFAULTDIR:
        logger.error('The output directory:[{0}] is the Download Directory. '
                     'Edit outputDirectory in autoProcessMedia.cfg. Exiting'.format
                     (inputDirectory))
        return [-1, ""]

    logger.debug("Scanning files in directory: {0}".format(inputDirectory))

    if sectionName in ['HeadPhones', 'Lidarr']:
        core.NOFLATTEN.extend(
            inputCategory)  # Make sure we preserve folder structure for HeadPhones.

    now = datetime.datetime.now()

    if extract == 1:
        inputFiles = core.listMediaFiles(inputDirectory, archives=False, other=True, otherext=extensions)
    else:
        inputFiles = core.listMediaFiles(inputDirectory, other=True, otherext=extensions)
    if len(inputFiles) == 0 and os.path.isfile(inputDirectory):
        inputFiles = [inputDirectory]
        logger.debug("Found 1 file to process: {0}".format(inputDirectory))
    else:
        logger.debug("Found {0} files in {1}".format(len(inputFiles), inputDirectory))
    for inputFile in inputFiles:
        filePath = os.path.dirname(inputFile)
        fileName, fileExt = os.path.splitext(os.path.basename(inputFile))
        fullFileName = os.path.basename(inputFile)

        targetFile = core.os.path.join(outputDestination, fullFileName)
        if inputCategory in core.NOFLATTEN:
            if not os.path.basename(filePath) in outputDestination:
                targetFile = core.os.path.join(
                    core.os.path.join(outputDestination, os.path.basename(filePath)), fullFileName)
                logger.debug("Setting outputDestination to {0} to preserve folder structure".format
                             (os.path.dirname(targetFile)))
        try:
            targetFile = targetFile.encode(core.SYS_ENCODING)
        except UnicodeError:
            pass
        if root == 1:
            if not foundFile:
                logger.debug("Looking for {0} in: {1}".format(inputName, inputFile))
            if any([core.sanitizeName(inputName) in core.sanitizeName(inputFile),
                    core.sanitizeName(fileName) in core.sanitizeName(inputName)]):
                foundFile = True
                logger.debug("Found file {0} that matches Torrent Name {1}".format
                             (fullFileName, inputName))
            else:
                continue

        if root == 2:
            mtime_lapse = now - datetime.datetime.fromtimestamp(os.path.getmtime(inputFile))
            ctime_lapse = now - datetime.datetime.fromtimestamp(os.path.getctime(inputFile))

            if not foundFile:
                logger.debug("Looking for files with modified/created dates less than 5 minutes old.")
            if (mtime_lapse < datetime.timedelta(minutes=5)) or (ctime_lapse < datetime.timedelta(minutes=5)):
                foundFile = True
                logger.debug("Found file {0} with date modified/created less than 5 minutes ago.".format
                             (fullFileName))
            else:
                continue  # This file has not been recently moved or created, skip it

        if Torrent_NoLink == 0:
            try:
                core.copy_link(inputFile, targetFile, core.USELINK)
                core.rmReadOnly(targetFile)
            except:
                logger.error("Failed to link: {0} to {1}".format(inputFile, targetFile))

    inputName, outputDestination = convert_to_ascii(inputName, outputDestination)

    if extract == 1:
        logger.debug('Checking for archives to extract in directory: {0}'.format(inputDirectory))
        core.extractFiles(inputDirectory, outputDestination, keep_archive)

    if inputCategory not in core.NOFLATTEN:
        # don't flatten hp in case multi cd albums, and we need to copy this back later.
        core.flatten(outputDestination)

    # Now check if video files exist in destination:
    if sectionName in ["SickBeard", "NzbDrone", "Sonarr", "CouchPotato", "Radarr"]:
        numVideos = len(
            core.listMediaFiles(outputDestination, media=True, audio=False, meta=False, archives=False))
        if numVideos > 0:
            logger.info("Found {0} media files in {1}".format(numVideos, outputDestination))
            status = 0
        elif extract != 1:
            logger.info("Found no media files in {0}. Sending to {1} to process".format(outputDestination, sectionName))
            status = 0
        else:
            logger.warning("Found no media files in {0}".format(outputDestination))

    # Only these sections can handling failed downloads
    # so make sure everything else gets through without the check for failed
    if sectionName not in ['CouchPotato', 'Radarr', 'SickBeard', 'NzbDrone', 'Sonarr']:
        status = 0

    logger.info("Calling {0}:{1} to post-process:{2}".format(sectionName, usercat, inputName))

    if core.TORRENT_CHMOD_DIRECTORY:
        core.rchmod(outputDestination, core.TORRENT_CHMOD_DIRECTORY)

    result = [0, ""]
    if sectionName == 'UserScript':
        result = external_script(outputDestination, inputName, inputCategory, section)

    elif sectionName in ['CouchPotato', 'Radarr']:
        result = core.autoProcessMovie().process(sectionName, outputDestination, inputName,
                                                 status, clientAgent, inputHash, inputCategory)
    elif sectionName in ['SickBeard', 'NzbDrone', 'Sonarr']:
        if inputHash:
            inputHash = inputHash.upper()
        result = core.autoProcessTV().processEpisode(sectionName, outputDestination, inputName,
                                                     status, clientAgent, inputHash, inputCategory)
    elif sectionName in ['HeadPhones', 'Lidarr']:
        result = core.autoProcessMusic().process(sectionName, outputDestination, inputName,
                                                 status, clientAgent, inputCategory)
    elif sectionName == 'Mylar':
        result = core.autoProcessComics().processEpisode(sectionName, outputDestination, inputName,
                                                         status, clientAgent, inputCategory)
    elif sectionName == 'Gamez':
        result = core.autoProcessGames().process(sectionName, outputDestination, inputName,
                                                 status, clientAgent, inputCategory)

    plex_update(inputCategory)

    if result[0] != 0:
        if not core.TORRENT_RESUME_ON_FAILURE:
            logger.error("A problem was reported in the autoProcess* script. "
                         "Torrent won't resume seeding (settings)")
        elif clientAgent != 'manual':
            logger.error("A problem was reported in the autoProcess* script. "
                         "If torrent was paused we will resume seeding")
            core.resume_torrent(clientAgent, inputHash, inputID, inputName)

    else:
        if clientAgent != 'manual':
            # update download status in our DB
            core.update_downloadInfoStatus(inputName, 1)

            # remove torrent
            if core.USELINK == 'move-sym' and not core.DELETE_ORIGINAL == 1:
                logger.debug('Checking for sym-links to re-direct in: {0}'.format(inputDirectory))
                for dirpath, dirs, files in os.walk(inputDirectory):
                    for file in files:
                        logger.debug('Checking symlink: {0}'.format(os.path.join(dirpath, file)))
                        replace_links(os.path.join(dirpath, file))
            core.remove_torrent(clientAgent, inputHash, inputID, inputName)

        if not sectionName == 'UserScript':
            # for user script, we assume this is cleaned by the script or option USER_SCRIPT_CLEAN
            # cleanup our processing folders of any misc unwanted files and empty directories
            core.cleanDir(outputDestination, sectionName, inputCategory)

    return result


def main(args):
    # Initialize the config
    core.initialize()

    # clientAgent for Torrents
    clientAgent = core.TORRENT_CLIENTAGENT

    logger.info("#########################################################")
    logger.info("## ..::[{0}]::.. ##".format(os.path.basename(__file__)))
    logger.info("#########################################################")

    # debug command line options
    logger.debug("Options passed into TorrentToMedia: {0}".format(args))

    # Post-Processing Result
    result = [0, ""]

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
                    logger.info("Starting manual run for {0}:{1} - Folder:{2}".format
                                (section, subsection, dirName))

                    logger.info("Checking database for download info for {0} ...".format
                                (os.path.basename(dirName)))
                    core.DOWNLOADINFO = core.get_downloadInfo(os.path.basename(dirName), 0)
                    if core.DOWNLOADINFO:
                        clientAgent = text_type(core.DOWNLOADINFO[0].get('client_agent', 'manual'))
                        inputHash = text_type(core.DOWNLOADINFO[0].get('input_hash', ''))
                        inputID = text_type(core.DOWNLOADINFO[0].get('input_id', ''))
                        logger.info("Found download info for {0}, "
                                    "setting variables now ...".format(os.path.basename(dirName)))
                    else:
                        logger.info('Unable to locate download info for {0}, '
                                    'continuing to try and process this release ...'.format
                                    (os.path.basename(dirName)))
                        clientAgent = 'manual'
                        inputHash = ''
                        inputID = ''

                    if clientAgent.lower() not in core.TORRENT_CLIENTS:
                        continue

                    try:
                        dirName = dirName.encode(core.SYS_ENCODING)
                    except UnicodeError:
                        pass
                    inputName = os.path.basename(dirName)
                    try:
                        inputName = inputName.encode(core.SYS_ENCODING)
                    except UnicodeError:
                        pass

                    results = processTorrent(dirName, inputName, subsection, inputHash or None, inputID or None,
                                             clientAgent)
                    if results[0] != 0:
                        logger.error("A problem was reported when trying to perform a manual run for {0}:{1}.".format
                                     (section, subsection))
                        result = results

    if result[0] == 0:
        logger.info("The {0} script completed successfully.".format(args[0]))
    else:
        logger.error("A problem was reported in the {0} script.".format(args[0]))
    del core.MYAPP
    return result[0]


if __name__ == "__main__":
    exit(main(sys.argv))
