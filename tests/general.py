import datetime
import os
import re
import nzbtomedia
import platform
from nzbtomedia.extractor import extractor
from nzbtomedia.nzbToMediaUtil import listMediaFiles, sanitizeFileName, \
    category_search, copy_link, flatten, remove_read_only, joinPath
from nzbtomedia import logger

status = int(1)  # 1 = failed | 0 = success
root = 0
video = 0
archive = 0
foundFile = 0
extracted_folder = []
copy_list = []

# Initialize the config
nzbtomedia.initialize()

inputDirectory = "Z:\complete\movie\The.Lego.Movie.2014.R5.x264.English.XviD-vTg.nfo_0166_-_The.Lego.Movie.2014.R5.x264.English.XviD-vTg.nfo_yEn.cp(tt1490017)"
inputName = "The.Lego.Movie.2014.R5.x264.English.XviD-vTg.nfo_0166_-_The.Lego.Movie.2014.R5.x264.English.XviD-vTg.nfo_yEn.cp(tt1490017)"
inputCategory = 'movie'

inputDirectory, inputName, inputCategory, root, single = category_search(inputDirectory, inputName, inputCategory, root, nzbtomedia.CATEGORIES)  # Confirm the category by parsing directory structure
outputDestination = os.path.normpath(joinPath(nzbtomedia.OUTPUTDIRECTORY, inputCategory, sanitizeFileName(inputName)))

logger.info("Scanning files in directory: %s" % (inputDirectory))

if nzbtomedia.CFG["HeadPhones"][inputCategory]:
    nzbtomedia.NOFLATTEN.extend(
        nzbtomedia.CFG["HeadPhones"].sections)  # Make sure we preserve folder structure for HeadPhones.

outputDestinationMaster = outputDestination  # Save the original, so we can change this within the loop below, and reset afterwards.
now = datetime.datetime.now()

inputFiles = listMediaFiles(inputDirectory)
logger.info("Found %s files in %s" % (str(len(inputFiles)), inputDirectory))
for inputFile in inputFiles:
    fileDirPath = os.path.dirname(inputFile)
    fileName, fileExt = os.path.splitext(os.path.basename(inputFile))
    fullFileName = os.path.basename(inputFile)

    if inputCategory in nzbtomedia.NOFLATTEN:
        if not fileDirPath == outputDestinationMaster:
            outputDestination = joinPath(outputDestinationMaster,
                                             fileDirPath)  # join this extra directory to output.
            logger.info("Setting outputDestination to %s to preserve folder structure" % (outputDestination))

    targetDirectory = joinPath(outputDestination, fullFileName)

    if root == 1:
        if not foundFile:
            logger.info("Looking for %s in: %s" % (inputName, fullFileName))
        if (sanitizeFileName(inputName) in sanitizeFileName(fullFileName)) or (
                    sanitizeFileName(fileName) in sanitizeFileName(inputName)):
            foundFile = True
            logger.info("Found file %s that matches Torrent Name %s" % (fullFileName, inputName))
        else:
            continue

    if root == 2:
        mtime_lapse = now - datetime.datetime.fromtimestamp(os.path.getmtime(inputFile))
        ctime_lapse = now - datetime.datetime.fromtimestamp(os.path.getctime(inputFile))

        if not foundFile:
            logger.info("Looking for files with modified/created dates less than 5 minutes old.")
        if (mtime_lapse < datetime.timedelta(minutes=5)) or (ctime_lapse < datetime.timedelta(minutes=5)):
            #pass  # This file does match the date time criteria
            foundFile = True
            logger.info("Found file %s with date modifed/created less than 5 minutes ago." % (fullFileName))
        else:
            continue  # This file has not been recently moved or created, skip it

    if fileExt in nzbtomedia.COMPRESSEDCONTAINER:
        if not (nzbtomedia.CFG["SickBeard"][inputCategory] and nzbtomedia.CFG["SickBeard"][inputCategory][
            "nzbExtractionBy"] == "Destination"):
            # find part numbers in second "extension" from right, if we have more than 1 compressed file in the same directory.
            if re.search(r'\d+', os.path.splitext(fileName)[1]) and fileDirPath in extracted_folder and not any(
                            item in os.path.splitext(fileName)[1] for item in ['.720p', '.1080p', '.x264']):
                part = int(re.search(r'\d+', os.path.splitext(fileName)[1]).group())
                if part == 1:  # we only want to extract the primary part.
                    logger.info("Found primary part of a multi-part archive %s. Extracting" % (fullFileName))
                else:
                    logger.info("Found part %s of a multi-part archive %s. Ignoring" % (part, fullFileName))
                    continue
            logger.info("Found compressed archive %s for file %s" % (fileExt, inputFile))
            try:
                extractor.extract(inputFile, outputDestination)
                extractionSuccess = True  # we use this variable to determine if we need to pause a torrent or not in uTorrent (don't need to pause archived content)
                extracted_folder.append(fileDirPath)
            except:
                logger.error("Extraction failed for: %s" % (fullFileName))
            continue

    try:
        copy_link(inputFile, targetDirectory, nzbtomedia.USELINK, outputDestination)
        copy_list.append([inputFile, joinPath(outputDestination, fullFileName)])
    except:
        logger.error("Failed to link file: %s" % (fullFileName))

outputDestination = outputDestinationMaster  # Reset here.
if not inputCategory in nzbtomedia.NOFLATTEN:  #don't flatten hp in case multi cd albums, and we need to copy this back later.
    flatten(outputDestination)

if platform.system() == 'Windows':  # remove Read Only flag from files in Windows.
    remove_read_only(outputDestination)

# Now check if video files exist in destination:
if nzbtomedia.CFG["SickBeard", "NzbDrone", "CouchPotato"][inputCategory]:
    for outputFile in listMediaFiles(outputDestination):
        fullFileName = os.path.basename(outputFile)
        fileName, fileExt = os.path.splitext(fullFileName)

        if fileExt in nzbtomedia.MEDIACONTAINER:
            logger.info("Found media file: %s" % (fullFileName))
            video += 1
        if fileExt in nzbtomedia.COMPRESSEDCONTAINER:
            logger.info("Found archive file: %s" % (fullFileName))
            archive += 1

    if video > 0:
        logger.info("Found %s media files" % (str(video)))
        status = 0
    elif archive > 0 and not nzbtomedia.CFG["SickBeard"][inputCategory]["nzbExtractionBy"] == "Destination":
        logger.info("Found %s archive files to be extracted by SickBeard" % (str(archive)))
        status = 0
    else:
        logger.warning("Found no media files in %s" % outputDestination)
