import os
import re
import socket
import stat
import struct
import shutil
import sys
import time
import nzbtomedia

from nzbtomedia.linktastic import linktastic
from nzbtomedia import logger
from nzbtomedia.synchronousdeluge.client import DelugeClient
from nzbtomedia.utorrent.client import UTorrentClient
from nzbtomedia.transmissionrpc.client import Client as TransmissionClient


def getDirectorySize(directory):
    dir_size = 0
    for (path, dirs, files) in os.walk(directory):
        for file in files:
            filename = os.path.join(path, file)
            dir_size += os.path.getsize(filename)
    dir_size = dir_size / (1024.0 * 1024.0 * 1024.0) # convert to GiB
    return dir_size


def safeName(name):
    safename = re.sub(r"[\/\\\:\*\?\"\<\>\|]", "", name) #make this name safe for use in directories for windows etc.
    return safename

def create_destination(outputDestination):
    if os.path.exists(outputDestination):
        return
    try:
        logger.info("CREATE DESTINATION: Creating destination folder: %s", outputDestination)
        os.makedirs(outputDestination)
    except:
        logger.error("CREATE DESTINATION: Not possible to create destination folder. Exiting")
        sys.exit(-1)

def makeDir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except OSError:
            return False
    return True

def category_search(inputDirectory, inputName, inputCategory, root, categories):
    single = False
    tordir = False

    if inputDirectory is None:  # =Nothing to process here.
        return inputDirectory, inputName, inputCategory, root, single

    pathlist = os.path.normpath(inputDirectory).split(os.sep)

    try:
        inputCategory = list(set(pathlist) & set(categories))[-1]  # assume last match is most relevant category.
        logger.debug("SEARCH: Found Category: %s in directory structure", inputCategory)
    except IndexError:
        inputCategory = ""
        logger.debug("SEARCH: Could not find a category in the directory structure")

    if not os.path.isdir(inputDirectory) and os.path.isfile(inputDirectory):  # If the input directory is a file
        single = True
        if not inputName: inputName = os.path.split(os.path.normpath(inputDirectory))[1]
        return inputDirectory, inputName, inputCategory, root, single

    if inputCategory and os.path.isdir(os.path.join(inputDirectory, inputCategory)):
        logger.info("SEARCH: Found category directory %s in input directory directory %s", inputCategory, inputDirectory)
        inputDirectory = os.path.join(inputDirectory, inputCategory)
        logger.info("SEARCH: Setting inputDirectory to %s", inputDirectory)
    if inputName and os.path.isdir(os.path.join(inputDirectory, inputName)):
        logger.info("SEARCH: Found torrent directory %s in input directory directory %s", inputName, inputDirectory)
        inputDirectory = os.path.join(inputDirectory, inputName)
        logger.info("SEARCH: Setting inputDirectory to %s", inputDirectory)
        tordir = True
    if inputName and os.path.isdir(os.path.join(inputDirectory, safeName(inputName))):
        logger.info("SEARCH: Found torrent directory %s in input directory directory %s", safeName(inputName), inputDirectory)
        inputDirectory = os.path.join(inputDirectory, safeName(inputName))
        logger.info("SEARCH: Setting inputDirectory to %s", inputDirectory)
        tordir = True

    imdbid = [item for item in pathlist if '.cp(tt' in item]  # This looks for the .cp(tt imdb id in the path.
    if imdbid and not '.cp(tt' in inputName:
        inputName = imdbid[0]  # This ensures the imdb id is preserved and passed to CP
        tordir = True

    if inputCategory and not tordir:
        try:
            index = pathlist.index(inputCategory)
            if index + 1 < len(pathlist):
                tordir = True
                logger.info("SEARCH: Found a unique directory %s in the category directory", pathlist[index+1])
                if not inputName: inputName = pathlist[index+1]
        except ValueError:
            pass

    if inputName and not tordir:
        if inputName in pathlist or safeName(inputName) in pathlist:
            logger.info("SEARCH: Found torrent directory %s in the directory structure", inputName)
            tordir = True
        else:
            root = 1
    if not tordir:
        root = 2

    if root > 0:
        logger.info("SEARCH: Could not find a unique directory for this download. Assume a common directory.")
        logger.info("SEARCH: We will try and determine which files to process, individually")

    return inputDirectory, inputName, inputCategory, root, single

def is_sample(filePath, inputName, minSampleSize, SampleIDs):
    # 200 MB in bytes
    SIZE_CUTOFF = minSampleSize * 1024 * 1024
    if os.path.getsize(filePath) < SIZE_CUTOFF:
        if 'SizeOnly' in SampleIDs:
            return True
        # Ignore 'sample' in files unless 'sample' in Torrent Name
        for ident in SampleIDs:
            if ident.lower() in filePath.lower() and not ident.lower() in inputName.lower(): 
                return True
    # Return False if none of these were met.
    return False


def copy_link(filePath, targetDirectory, useLink, outputDestination):
    if os.path.isfile(targetDirectory):
        logger.info("COPYLINK: target file already exists. Nothing to be done")
        return True

    create_destination(outputDestination)
    if useLink == "hard":
        try:
            logger.info("COPYLINK: Hard linking %s to %s", filePath, targetDirectory)
            linktastic.link(filePath, targetDirectory)
        except:
            logger.error("COPYLINK")
            if os.path.isfile(targetDirectory):
                logger.warning("COPYLINK: Something went wrong in linktastic.link, but the destination file was created")
            else:
                logger.warning("COPYLINK: Something went wrong in linktastic.link, copying instead")
                logger.debug("COPYLINK: Copying %s to %s", filePath, targetDirectory)
                shutil.copy(filePath, targetDirectory)
    elif useLink == "sym":
        try:
            logger.info("COPYLINK: Moving %s to %s before sym linking", filePath, targetDirectory)
            shutil.move(filePath, targetDirectory)
            logger.info("COPYLINK: Sym linking %s to %s", targetDirectory, filePath)
            linktastic.symlink(targetDirectory, filePath)
        except:
            logger.error("COPYLINK")
            if os.path.isfile(targetDirectory):
                logger.warning("COPYLINK: Something went wrong in linktastic.link, but the destination file was created")
            else:
                logger.info("COPYLINK: Something went wrong in linktastic.link, copying instead")
                logger.debug("COPYLINK: Copying %s to %s", filePath, targetDirectory)
                shutil.copy(filePath, targetDirectory)
    elif useLink == "move":
        logger.debug("Moving %s to %s", filePath, targetDirectory)
        shutil.move(filePath, targetDirectory)
    else:
        logger.debug("Copying %s to %s", filePath, targetDirectory)
        shutil.copy(filePath, targetDirectory)
    return True


def flatten(outputDestination):
    logger.info("FLATTEN: Flattening directory: %s", outputDestination)
    for dirpath, dirnames, filenames in os.walk(outputDestination):  # Flatten out the directory to make postprocessing easier
        if dirpath == outputDestination:
            continue  # No need to try and move files in the root destination directory
        for filename in filenames:
            source = os.path.join(dirpath, filename)
            target = os.path.join(outputDestination, filename)
            try:
                shutil.move(source, target)
            except:
                logger.error("FLATTEN: Could not flatten %s", source)
    removeEmptyFolders(outputDestination)  # Cleanup empty directories


def removeEmptyFolders(path):
    logger.info("REMOVER: Removing empty folders in: %s", path)
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
        logger.debug("REMOVER: Removing empty folder: %s", path)
        os.rmdir(path)

def remove_read_only(path):
    if not os.path.isdir(path):
        return
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            logger.debug("Removing Read Only Flag for: %s", filename)
            os.chmod(os.path.join(dirpath, filename), stat.S_IWRITE)

def iterate_media_files(dirname):
    mediaContainer = [ '.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv',
        '.mp4', '.mpg', '.mpeg', '.iso' ]

    for dirpath, dirnames, filenames in os.walk(dirname):
        for filename in filenames:
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
    if not nzbtomedia.CFG:
        logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return

    wake = int(nzbtomedia.CFG["WakeOnLan"]["wake"])
    if wake == 0: # just return if we don't need to wake anything.
        return
    logger.info(("Loading WakeOnLan config from %s", nzbtomedia.CONFIG_FILE))
    host = nzbtomedia.CFG["WakeOnLan"]["host"]
    port = int(nzbtomedia.CFG["WakeOnLan"]["port"])
    mac = nzbtomedia.CFG["WakeOnLan"]["mac"]

    i=1
    while TestCon(host, port) == "Down" and i < 4:
        logger.info(("Sending WakeOnLan Magic Packet for mac: %s", mac))
        WakeOnLan(mac)
        time.sleep(20)
        i=i+1

    if TestCon(host,port) == "Down": # final check.
        logger.warning("System with mac: %s has not woken after 3 attempts. Continuing with the rest of the script.", mac)
    else:
        logger.info("System with mac: %s has been woken. Continuing with the rest of the script.", mac)

def convert_to_ascii(nzbName, dirName):
    if not nzbtomedia.CFG:
        logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return nzbName, dirName

    ascii_convert = int(nzbtomedia.CFG["ASCII"]["convert"])
    if ascii_convert == 0 or os.name == 'nt': # just return if we don't want to convert or on windows os and "\" is replaced!.
        return nzbName, dirName
    
    nzbName2 = str(nzbName.decode('ascii', 'replace').replace(u'\ufffd', '_'))
    dirName2 = str(dirName.decode('ascii', 'replace').replace(u'\ufffd', '_'))
    if dirName != dirName2:
        logger.info("Renaming directory:%s  to: %s.", dirName, dirName2)
        shutil.move(dirName, dirName2)
    for dirpath, dirnames, filesnames in os.walk(dirName2):
        for filename in filesnames:
            filename2 = str(filename.decode('ascii', 'replace').replace(u'\ufffd', '_'))
            if filename != filename2:
                logger.info("Renaming file:%s  to: %s.", filename, filename2)
                shutil.move(filename, filename2)
    nzbName = nzbName2
    dirName = dirName2
    return nzbName, dirName

def parse_other(args):

    return os.path.normpath(args[1]), '', '', '', ''

def parse_rtorrent(args):
    # rtorrent usage: system.method.set_key = event.download.finished,TorrentToMedia,
    # "execute={/path/to/nzbToMedia/TorrentToMedia.py,\"$d.get_base_path=\",\"$d.get_name=\",\"$d.get_custom1=\",\"$d.get_hash=\"}"
    inputDirectory = os.path.normpath(args[1])
    try:
        inputName = args[2]
    except:
        inputName = ''
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
    inputDirectory = os.path.normpath(args[3])
    inputName = args[2]
    inputCategory = ''  # We dont have a category yet
    inputHash = args[1]
    inputID = args[1]
    return inputDirectory, inputName, inputCategory, inputHash, inputID


def parse_transmission(args):
    # Transmission usage: call TorrenToMedia.py (%TR_TORRENT_DIR% %TR_TORRENT_NAME% is passed on as environmental variables)
    inputDirectory = os.path.normpath(os.getenv('TR_TORRENT_DIR'))
    inputName = os.getenv('TR_TORRENT_NAME')
    inputCategory = ''  # We dont have a category yet
    inputHash = os.getenv('TR_TORRENT_HASH')
    inputID = os.getenv('TR_TORRENT_ID')
    return inputDirectory, inputName, inputCategory, inputHash, inputID

def parse_args(clientAgent, args):
    clients = {
    'other': parse_other,
    'rtorrent': parse_rtorrent,
    'utorrent': parse_utorrent,
    'deluge': parse_deluge,
    'transmission': parse_transmission,
    }

    try:
        return clients[clientAgent](args)
    except:return None, None, None, None, None

def get_dirnames(section, subsections=None):

    dirNames = []

    if subsections is None:
        subsections = nzbtomedia.SUBSECTIONS[section].sections

    if not isinstance(subsections, list):
        subsections = [subsections]

    for subsection in subsections:
        try:
            watch_dir = nzbtomedia.CFG[section][subsection]["watch_dir"]
            if not os.path.exists(watch_dir):
                watch_dir = None
        except:
            watch_dir = None

        try:
            outputDirectory = os.path.join(nzbtomedia.CFG["Torrent"]["outputDirectory"], subsection)
            if not os.path.exists(outputDirectory):
                outputDirectory = None
        except:
            outputDirectory = None

        if watch_dir:
            dirNames.extend([os.path.join(watch_dir, o) for o in os.listdir(watch_dir) if
                        os.path.isdir(os.path.join(watch_dir, o))])

        if outputDirectory:
            dirNames.extend([os.path.join(outputDirectory, o) for o in os.listdir(outputDirectory) if
                        os.path.isdir(os.path.join(outputDirectory, o))])

        if not dirNames:
            logger.warning("%s:%s has no directories identified for post-processing", section, subsection)

    return list(set(dirNames))

def delete(dirName):
    logger.info("Deleting %s", dirName)
    try:
        shutil.rmtree(dirName, True)
    except:
        logger.error("Unable to delete folder %s", dirName)

def cleanup_directories(inputCategory, processCategories, result, directory):
    if inputCategory in processCategories and result == 0 and os.path.isdir(directory):
        num_files_new = int(0)
        file_list = []
        for dirpath, dirnames, filenames in os.walk(directory):
            for file in filenames:
                filePath = os.path.join(dirpath, file)
                fileName, fileExtension = os.path.splitext(file)
                if fileExtension in nzbtomedia.MEDIACONTAINER or fileExtension in nzbtomedia.METACONTAINER:
                    num_files_new += 1
                    file_list.append(file)
        if num_files_new is 0 or int(nzbtomedia.CFG["General"]["force_clean"]) == 1:
            logger.info("All files have been processed. Cleaning directory %s", directory)
            shutil.rmtree(directory)
        else:
            logger.info("Directory %s still contains %s media and/or meta files. This directory will not be removed.", directory, num_files_new)
            for item in file_list:
                logger.debug("media/meta file found: %s", item)

def create_torrent_class(clientAgent):
    # Hardlink solution for Torrents
    TorrentClass = ""
    if clientAgent in ['utorrent', 'transmission', 'deluge']:
        if clientAgent == 'utorrent':
            try:
                logger.debug("Connecting to %s: %s", clientAgent, nzbtomedia.UTORRENTWEBUI)
                TorrentClass = UTorrentClient(nzbtomedia.UTORRENTWEBUI, nzbtomedia.UTORRENTUSR, nzbtomedia.UTORRENTPWD)
            except:
                logger.error("Failed to connect to uTorrent")

        if clientAgent == 'transmission':
            try:
                logger.debug("Connecting to %s: http://%s:%s", clientAgent, nzbtomedia.TRANSMISSIONHOST,
                             nzbtomedia.TRANSMISSIONPORT)
                TorrentClass = TransmissionClient(nzbtomedia.TRANSMISSIONHOST, nzbtomedia.TRANSMISSIONPORT, nzbtomedia.TRANSMISSIONUSR,
                                                  nzbtomedia.TRANSMISSIONPWD)
            except:
                logger.error("Failed to connect to Transmission")

        if clientAgent == 'deluge':
            try:
                logger.debug("Connecting to %s: http://%s:%s", clientAgent, nzbtomedia.DELUGEHOST,
                             nzbtomedia.DELUGEPORT)
                TorrentClass = DelugeClient()
                TorrentClass.connect(host =nzbtomedia.DELUGEHOST, port =nzbtomedia.DELUGEPORT, username =nzbtomedia.DELUGEUSR, password =nzbtomedia.DELUGEPWD)
            except:
                logger.error("Failed to connect to deluge")

    return TorrentClass