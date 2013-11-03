import logging
import logging.config
import os
import re
import sys
import shutil
import struct
import socket
import time
import ConfigParser

import linktastic.linktastic as linktastic

Logger = logging.getLogger()


def safeName(name):
    safename = re.sub(r"[\/\\\:\*\?\"\<\>\|]", "", name) #make this name safe for use in directories for windows etc.
    return safename


def nzbtomedia_configure_logging(dirname):
    logFile = os.path.join(dirname, "postprocess.log")
    logging.config.fileConfig(os.path.join(dirname, "autoProcessMedia.cfg"))
    fileHandler = logging.handlers.RotatingFileHandler(logFile, mode='a', maxBytes=1048576, backupCount=1, encoding='utf-8', delay=True)
    fileHandler.formatter = logging.Formatter('%(asctime)s|%(levelname)-7.7s %(message)s', '%H:%M:%S')
    fileHandler.level = logging.DEBUG
    logging.getLogger().addHandler(fileHandler)


def create_destination(outputDestination):
    if os.path.exists(outputDestination):
        return
    try:
        Logger.info("CREATE DESTINATION: Creating destination folder: %s", outputDestination)
        os.makedirs(outputDestination)
    except:
        Logger.exception("CREATE DESTINATION: Not possible to create destination folder. Exiting")
        sys.exit(-1)

def category_search(inputDirectory, inputName, inputCategory, root, categories):
    if inputCategory and os.path.isdir(os.path.join(inputDirectory, inputCategory)):
        Logger.info("SEARCH: Found category directory %s in input directory directory %s", inputCategory, inputDirectory)
        inputDirectory = os.path.join(inputDirectory, inputCategory)
        Logger.info("SEARCH: Setting inputDirectory to %s", inputDirectory)
    if inputName os.path.isdir(os.path.join(inputDirectory, inputName)):
        Logger.info("SEARCH: Found torrent directory %s in input directory directory %s", inputName, inputDirectory)
        inputDirectory = os.path.join(inputDirectory, inputName)
        Logger.info("SEARCH: Setting inputDirectory to %s", inputDirectory)
    if inputName os.path.isdir(os.path.join(inputDirectory, safeName(inputName))):
        Logger.info("SEARCH: Found torrent directory %s in input directory directory %s", safeName(inputName), inputDirectory)
        inputDirectory = os.path.join(inputDirectory, safeName(inputName))
        Logger.info("SEARCH: Setting inputDirectory to %s", inputDirectory)
    
    categorySearch = [os.path.normpath(inputDirectory), ""]  # initializie
    notfound = 0
    for x in range(10):  # loop up through 10 directories looking for category.
        try:
            categorySearch2 = os.path.split(os.path.normpath(categorySearch[0]))
        except:  # this might happen when we can't go higher.
            if inputCategory and inputName:  # if these exists, we are ok to proceed, but assume we are in a root/common directory.
                Logger.info("SEARCH: Could not find a category in the directory structure")
                Logger.info("SEARCH: We will try and determine which files to process, individually")
                root = 1
                break  # we are done
            elif inputCategory:  # if this exists, we are ok to proceed, but assume we are in a root/common directory and we have to check file dates.
                Logger.info("SEARCH: Could not find a torrent name or category in the directory structure")
                Logger.info("SEARCH: We will try and determine which files to process, individually")
                root = 2
                break  # we are done
            elif inputName:  # we didn't find category after 10 loops. This is a problem.
                Logger.info("SEARCH: Could not find a category in the directory structure")
                Logger.info("SEARCH: Files will be linked and will only be processed by the userscript if enabled for UNCAT or ALL")
                root = 1
                break  # we are done
            else:  # we didn't find this after 10 loops. This is a problem.
                Logger.info("SEARCH: Could not identify category or torrent name from the directory structure.")
                Logger.info("SEARCH: Files will be linked and will only be processed by the userscript if enabled for UNCAT or ALL")
                root = 2
                break  # we are done

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
            elif inputName and os.path.isdir(os.path.join(categorySearch[0], inputName)):  # testing for torrent name in first sub directory
                Logger.info("SEARCH: Found torrent directory %s in category directory %s", os.path.join(categorySearch[0], inputName), categorySearch[0])
                if categorySearch[0] == os.path.normpath(inputDirectory):  # only true on first pass, x =0
                    inputDirectory = os.path.join(categorySearch[0], inputName)  # we only want to search this next dir up.
                break  # we are done
            elif inputName and os.path.isdir(os.path.join(categorySearch[0], safeName(inputName))):  # testing for torrent name in first sub directory
                Logger.info("SEARCH: Found torrent directory %s in category directory %s", os.path.join(categorySearch[0], safeName(inputName)), categorySearch[0])
                if categorySearch[0] == os.path.normpath(inputDirectory):  # only true on first pass, x =0
                    inputDirectory = os.path.join(categorySearch[0], safeName(inputName))  # we only want to search this next dir up.
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
        elif inputName and safeName(categorySearch2[1]) == safeName(inputName):  # we have identified a unique directory.
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
            Logger.info("SEARCH: We will try and determine which files to process, individually")
            root = 1
        elif inputCategory:  # if this exists, we are ok to proceed, but assume we are in a root/common directory and we have to check file dates.
            Logger.info("SEARCH: Could not find a torrent name or category in the directory structure")
            Logger.info("SEARCH: We will try and determine which files to process, individually")
            root = 2
        elif inputName:  # we didn't find category after 10 loops. This is a problem.
            Logger.info("SEARCH: Could not find a category in the directory structure")
            Logger.info("SEARCH: Files will be linked and will only be processed by the userscript if enabled for UNCAT or ALL")
            root = 1
        else:  # we didn't find this after 10 loops. This is a problem.
            Logger.info("SEARCH: Could not identify category or torrent name from the directory structure.")
            Logger.info("SEARCH: Files will be linked and will only be processed by the userscript if enabled for UNCAT or ALL")
            root = 2

    return inputDirectory, inputName, inputCategory, root


def is_sample(filePath, inputName, minSampleSize):
    # 200 MB in bytes
    SIZE_CUTOFF = minSampleSize * 1024 * 1024
    # Ignore 'sample' in files unless 'sample' in Torrent Name
    return ('sample' in filePath.lower()) and (not 'sample' in inputName) and (os.path.getsize(filePath) < SIZE_CUTOFF)


def copy_link(filePath, targetDirectory, useLink, outputDestination):
    if os.path.isfile(targetDirectory):
        Logger.info("COPYLINK: target file already exists. Nothing to be done")
        return True

    create_destination(outputDestination)
    if useLink == "hard":
        try:
            Logger.info("COPYLINK: Hard linking %s to %s", filePath, targetDirectory)
            linktastic.link(filePath, targetDirectory)
        except:
            Logger.exception("COPYLINK")
            if os.path.isfile(targetDirectory):
                Logger.warn("COPYLINK: Something went wrong in linktastic.link, but the destination file was created")
            else:
                Logger.warn("COPYLINK: Something went wrong in linktastic.link, copying instead")
                Logger.debug("COPYLINK: Copying %s to %s", filePath, targetDirectory)
                shutil.copy(filePath, targetDirectory)
    elif useLink == "sym":
        try:
            Logger.info("COPYLINK: Moving %s to %s before sym linking", filePath, targetDirectory)
            shutil.move(filePath, targetDirectory)
            Logger.info("COPYLINK: Sym linking %s to %s", targetDirectory, filePath)
            linktastic.symlink(targetDirectory, filePath)
        except:
            Logger.exception("COPYLINK")
            if os.path.isfile(targetDirectory):
                Logger.warn("COPYLINK: Something went wrong in linktastic.link, but the destination file was created")
            else:
                Logger.info("COPYLINK: Something went wrong in linktastic.link, copying instead")
                Logger.debug("COPYLINK: Copying %s to %s", filePath, targetDirectory)
                shutil.copy(filePath, targetDirectory)
    elif useLink == "move":
        Logger.debug("Moving %s to %s", filePath, targetDirectory)
        shutil.move(filePath, targetDirectory)
    else:
        Logger.debug("Copying %s to %s", filePath, targetDirectory)
        shutil.copy(filePath, targetDirectory)
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
            except:
                Logger.exception("FLATTEN: Could not flatten %s", source)
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

def iterate_media_files(dirname):
    mediaContainer = [ '.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv',
        '.mp4', '.mpg', '.mpeg', '.iso' ]

    for dirpath, dirnames, filesnames in os.walk(dirname):
        for filename in filesnames:
            fileExtension = os.path.splitext(filename)[1]
            if not (fileExtension in mediaContainer):
                continue
            yield dirpath, os.path.join(dirpath, filename)


#Wake function
def WakeOnLan(ethernet_address):

    addr_byte = ethernet_address.split(':')
    hw_addr = struct.pack('BBBBBB', int(addr_byte[0], 16),
    int(addr_byte[1], 16),
    int(addr_byte[2], 16),
    int(addr_byte[3], 16),
    int(addr_byte[4], 16),
    int(addr_byte[5], 16))

    # Build the Wake-On-LAN "Magic Packet"...

    msg = '\xff' * 6 + hw_addr * 16

    # ...and send it to the broadcast address using UDP

    ss = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ss.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    ss.sendto(msg, ('<broadcast>', 9))
    ss.close()


#Test Connection function
def TestCon(host, port):
    try:
        socket.create_connection((host, port))
        return "Up"
    except:
        return "Down"


def WakeUp():
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return

    config.read(configFilename)
    wake = int(config.get("WakeOnLan", "wake"))
    if wake == 0: # just return if we don't need to wake anything.
        return
    Logger.info("Loading WakeOnLan config from %s", configFilename)
    config.get("WakeOnLan", "host")
    host = config.get("WakeOnLan", "host")
    port = int(config.get("WakeOnLan", "port"))
    mac = config.get("WakeOnLan", "mac")

    i=1
    while TestCon(host, port) == "Down" and i < 4:
        Logger.info("Sending WakeOnLan Magic Packet for mac: %s", mac)
        WakeOnLan(mac)
        time.sleep(20)
        i=i+1

    if TestCon(host,port) == "Down": # final check.
        Logger.warning("System with mac: %s has not woken after 3 attempts. Continuing with the rest of the script.", mac)
    else:
        Logger.info("System with mac: %s has been woken. Continuing with the rest of the script.", mac)


def parse_other(args):
    return os.path.normpath(sys.argv[1]), '', '', '', ''


def parse_utorrent(args):
    # uTorrent usage: call TorrentToMedia.py "%D" "%N" "%L" "%I"
    inputDirectory = os.path.normpath(args[1])
    inputName = args[2]
    try:
        inputCategory = args[3]
    except:
        inputCategory = ''
    try:
        inputHash = args[4]
    except:
        inputHash = ''
    try:
        inputID = args[4]
    except:
        inputID = ''

    return inputDirectory, inputName, inputCategory, inputHash, inputID


def parse_deluge(args):
    # Deluge usage: call TorrentToMedia.py TORRENT_ID TORRENT_NAME TORRENT_DIR
    inputDirectory = os.path.normpath(sys.argv[3])
    inputName = sys.argv[2]
    inputCategory = ''  # We dont have a category yet
    inputHash = ''
    inputID = sys.argv[1]
    return inputDirectory, inputName, inputCategory, inputHash, inputID


def parse_transmission(args):
    # Transmission usage: call TorrenToMedia.py (%TR_TORRENT_DIR% %TR_TORRENT_NAME% is passed on as environmental variables)
    inputDirectory = os.path.normpath(os.getenv('TR_TORRENT_DIR'))
    inputName = os.getenv('TR_TORRENT_NAME')
    inputCategory = ''  # We dont have a category yet
    inputHash = os.getenv('TR_TORRENT_HASH')
    inputID = os.getenv('TR_TORRENT_ID')
    return inputDirectory, inputName, inputCategory, inputHash, inputID


__ARG_PARSERS__ = {
    'other': parse_other,
    'utorrent': parse_utorrent,
    'deluge': parse_deluge,
    'transmission': parse_transmission,
}


def parse_args(clientAgent):
    parseFunc = __ARG_PARSERS__.get(clientAgent, None)
    if not parseFunc:
        raise RuntimeError("Could not find client-agent")
    return parseFunc(sys.argv)
