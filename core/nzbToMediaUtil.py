# coding=utf-8

from __future__ import print_function, unicode_literals
from six import text_type
import os
import re
import socket
import stat
import struct
import shutil
import time
import datetime
import platform
import guessit
import beets
import requests
import core
from babelfish import Language
import subliminal

from core.extractor import extractor
from core.linktastic import linktastic
from core.synchronousdeluge.client import DelugeClient
from core.utorrent.client import UTorrentClient
from core.transmissionrpc.client import Client as TransmissionClient
from core.qbittorrent.client import Client as qBittorrentClient
from core import logger, nzbToMediaDB

requests.packages.urllib3.disable_warnings()

# Monkey Patch shutil.copyfileobj() to adjust the buffer length to 512KB rather than 4KB
shutil.copyfileobjOrig = shutil.copyfileobj
def copyfileobjFast(fsrc, fdst, length=512*1024):
    shutil.copyfileobjOrig(fsrc, fdst, length=length)
shutil.copyfileobj = copyfileobjFast

def reportNzb(failure_link, clientAgent):
    # Contact indexer site
    logger.info("Sending failure notification to indexer site")
    if clientAgent == 'nzbget':
        headers = {'User-Agent': 'NZBGet / nzbToMedia.py'}
    elif clientAgent == 'sabnzbd':
        headers = {'User-Agent': 'SABnzbd / nzbToMedia.py'}
    else:
        return
    try:
        requests.post(failure_link, headers=headers, timeout=(30, 300))
    except Exception as e:
        logger.error("Unable to open URL {0} due to {1}".format(failure_link, e))
    return


def sanitizeName(name):
    """
    >>> sanitizeName('a/b/c')
    'a-b-c'
    >>> sanitizeName('abc')
    'abc'
    >>> sanitizeName('a"b')
    'ab'
    >>> sanitizeName('.a.b..')
    'a.b'
    """

    # remove bad chars from the filename
    name = re.sub(r'[\\\/*]', '-', name)
    name = re.sub(r'[:"<>|?]', '', name)

    # remove leading/trailing periods and spaces
    name = name.strip(' .')
    try:
        name = name.encode(core.SYS_ENCODING)
    except:
        pass

    return name


def makeDir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except Exception:
            return False
    return True


def remoteDir(path):
    if not core.REMOTEPATHS:
        return path
    for local, remote in core.REMOTEPATHS:
        if local in path:
            base_dirs = path.replace(local, "").split(os.sep)
            if '/' in remote:
                remote_sep = '/'
            else:
                remote_sep = '\\'
            new_path = remote_sep.join([remote] + base_dirs)
            new_path = re.sub(r'(\S)(\\+)', r'\1\\', new_path)
            new_path = re.sub(r'(\/+)', r'/', new_path)
            new_path = re.sub(r'([\/\\])$', r'', new_path)
            return new_path
    return path


def category_search(inputDirectory, inputName, inputCategory, root, categories):
    tordir = False

    try:
        inputName = inputName.encode(core.SYS_ENCODING)
    except:
        pass
    try:
        inputDirectory = inputDirectory.encode(core.SYS_ENCODING)
    except:
        pass

    if inputDirectory is None:  # =Nothing to process here.
        return inputDirectory, inputName, inputCategory, root

    pathlist = os.path.normpath(inputDirectory).split(os.sep)

    if inputCategory and inputCategory in pathlist:
        logger.debug("SEARCH: Found the Category: {0} in directory structure".format(inputCategory))
    elif inputCategory:
        logger.debug("SEARCH: Could not find the category: {0} in the directory structure".format(inputCategory))
    else:
        try:
            inputCategory = list(set(pathlist) & set(categories))[-1]  # assume last match is most relevant category.
            logger.debug("SEARCH: Found Category: {0} in directory structure".format(inputCategory))
        except IndexError:
            inputCategory = ""
            logger.debug("SEARCH: Could not find a category in the directory structure")
    if not os.path.isdir(inputDirectory) and os.path.isfile(inputDirectory):  # If the input directory is a file
        if not inputName:
            inputName = os.path.split(os.path.normpath(inputDirectory))[1]
        return inputDirectory, inputName, inputCategory, root

    if inputCategory and os.path.isdir(os.path.join(inputDirectory, inputCategory)):
        logger.info(
            "SEARCH: Found category directory {0} in input directory directory {1}".format(inputCategory, inputDirectory))
        inputDirectory = os.path.join(inputDirectory, inputCategory)
        logger.info("SEARCH: Setting inputDirectory to {0}".format(inputDirectory))
    if inputName and os.path.isdir(os.path.join(inputDirectory, inputName)):
        logger.info("SEARCH: Found torrent directory {0} in input directory directory {1}".format(inputName, inputDirectory))
        inputDirectory = os.path.join(inputDirectory, inputName)
        logger.info("SEARCH: Setting inputDirectory to {0}".format(inputDirectory))
        tordir = True
    elif inputName and os.path.isdir(os.path.join(inputDirectory, sanitizeName(inputName))):
        logger.info("SEARCH: Found torrent directory {0} in input directory directory {1}".format(
            sanitizeName(inputName), inputDirectory))
        inputDirectory = os.path.join(inputDirectory, sanitizeName(inputName))
        logger.info("SEARCH: Setting inputDirectory to {0}".format(inputDirectory))
        tordir = True
    elif inputName and os.path.isfile(os.path.join(inputDirectory, inputName)):
        logger.info("SEARCH: Found torrent file {0} in input directory directory {1}".format(inputName, inputDirectory))
        inputDirectory = os.path.join(inputDirectory, inputName)
        logger.info("SEARCH: Setting inputDirectory to {0}".format(inputDirectory))
        tordir = True
    elif inputName and os.path.isfile(os.path.join(inputDirectory, sanitizeName(inputName))):
        logger.info("SEARCH: Found torrent file {0} in input directory directory {1}".format(
            sanitizeName(inputName), inputDirectory))
        inputDirectory = os.path.join(inputDirectory, sanitizeName(inputName))
        logger.info("SEARCH: Setting inputDirectory to {0}".format(inputDirectory))
        tordir = True

    imdbid = [item for item in pathlist if '.cp(tt' in item]  # This looks for the .cp(tt imdb id in the path.
    if imdbid and '.cp(tt' not in inputName:
        inputName = imdbid[0]  # This ensures the imdb id is preserved and passed to CP
        tordir = True

    if inputCategory and not tordir:
        try:
            index = pathlist.index(inputCategory)
            if index + 1 < len(pathlist):
                tordir = True
                logger.info("SEARCH: Found a unique directory {0} in the category directory".format
                            (pathlist[index + 1]))
                if not inputName:
                    inputName = pathlist[index + 1]
        except ValueError:
            pass

    if inputName and not tordir:
        if inputName in pathlist or sanitizeName(inputName) in pathlist:
            logger.info("SEARCH: Found torrent directory {0} in the directory structure".format(inputName))
            tordir = True
        else:
            root = 1
    if not tordir:
        root = 2

    if root > 0:
        logger.info("SEARCH: Could not find a unique directory for this download. Assume a common directory.")
        logger.info("SEARCH: We will try and determine which files to process, individually")

    return inputDirectory, inputName, inputCategory, root


def getDirSize(inputPath):
    from functools import partial
    prepend = partial(os.path.join, inputPath)
    return sum(
        [(os.path.getsize(f) if os.path.isfile(f) else getDirSize(f)) for f in map(prepend, os.listdir(unicode(inputPath)))])


def is_minSize(inputName, minSize):
    fileName, fileExt = os.path.splitext(os.path.basename(inputName))

    # audio files we need to check directory size not file size
    inputSize = os.path.getsize(inputName)
    if fileExt in core.AUDIOCONTAINER:
        try:
            inputSize = getDirSize(os.path.dirname(inputName))
        except:
            logger.error("Failed to get file size for {0}".format(inputName), 'MINSIZE')
            return True

    # Ignore files under a certain size
    if inputSize > minSize * 1048576:
        return True


def is_sample(inputName):
    # Ignore 'sample' in files
    if re.search('(^|[\W_])sample\d*[\W_]', inputName.lower()):
        return True


def copy_link(src, targetLink, useLink):
    logger.info("MEDIAFILE: [{0}]".format(os.path.basename(targetLink)), 'COPYLINK')
    logger.info("SOURCE FOLDER: [{0}]".format(os.path.dirname(src)), 'COPYLINK')
    logger.info("TARGET FOLDER: [{0}]".format(os.path.dirname(targetLink)), 'COPYLINK')

    if src != targetLink and os.path.exists(targetLink):
        logger.info("MEDIAFILE already exists in the TARGET folder, skipping ...", 'COPYLINK')
        return True
    elif src == targetLink and os.path.isfile(targetLink) and os.path.isfile(src):
        logger.info("SOURCE AND TARGET files are the same, skipping ...", 'COPYLINK')
        return True
    elif src == os.path.dirname(targetLink):
        logger.info("SOURCE AND TARGET folders are the same, skipping ...", 'COPYLINK')
        return True

    makeDir(os.path.dirname(targetLink))
    try:
        if useLink == 'dir':
            logger.info("Directory linking SOURCE FOLDER -> TARGET FOLDER", 'COPYLINK')
            linktastic.dirlink(src, targetLink)
            return True
        if useLink == 'junction':
            logger.info("Directory junction linking SOURCE FOLDER -> TARGET FOLDER", 'COPYLINK')
            linktastic.dirlink(src, targetLink)
            return True
        elif useLink == "hard":
            logger.info("Hard linking SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
            linktastic.link(src, targetLink)
            return True
        elif useLink == "sym":
            logger.info("Sym linking SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
            linktastic.symlink(src, targetLink)
            return True
        elif useLink == "move-sym":
            logger.info("Sym linking SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
            shutil.move(src, targetLink)
            linktastic.symlink(targetLink, src)
            return True
        elif useLink == "move":
            logger.info("Moving SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
            shutil.move(src, targetLink)
            return True
    except Exception as e:
        logger.warning("Error: {0}, copying instead ... ".format(e), 'COPYLINK')

    logger.info("Copying SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
    shutil.copy(src, targetLink)

    return True


def replace_links(link):
    n = 0
    target = link
    if os.name == 'nt':
        import jaraco
        if not jaraco.windows.filesystem.islink(link):
            logger.debug('{0} is not a link'.format(link))
            return
        while jaraco.windows.filesystem.islink(target):
            target = jaraco.windows.filesystem.readlink(target)
            n = n + 1
    else:
        if not os.path.islink(link):
            logger.debug('{0} is not a link'.format(link))
            return
        while os.path.islink(target):
            target = os.readlink(target)
            n = n + 1
    if n > 1:
        logger.info("Changing sym-link: {0} to point directly to file: {1}".format(link, target), 'COPYLINK')
        os.unlink(link)
        linktastic.symlink(target, link)


def flatten(outputDestination):
    logger.info("FLATTEN: Flattening directory: {0}".format(outputDestination))
    for outputFile in listMediaFiles(outputDestination):
        dirPath = os.path.dirname(outputFile)
        fileName = os.path.basename(outputFile)

        if dirPath == outputDestination:
            continue

        target = os.path.join(outputDestination, fileName)

        try:
            shutil.move(outputFile, target)
        except:
            logger.error("Could not flatten {0}".format(outputFile), 'FLATTEN')

    removeEmptyFolders(outputDestination)  # Cleanup empty directories


def removeEmptyFolders(path, removeRoot=True):
    """Function to remove empty folders"""
    if not os.path.isdir(path):
        return

    # remove empty subfolders
    logger.debug("Checking for empty folders in:{0}".format(path))
    files = os.listdir(unicode(path))
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                removeEmptyFolders(fullpath)

    # if folder empty, delete it
    files = os.listdir(unicode(path))
    if len(files) == 0 and removeRoot:
        logger.debug("Removing empty folder:{}".format(path))
        os.rmdir(path)


def rmReadOnly(filename):
    if os.path.isfile(filename):
        # check first the read-only attribute
        file_attribute = os.stat(filename)[0]
        if not file_attribute & stat.S_IWRITE:
            # File is read-only, so make it writeable
            logger.debug('Read only mode on file {name}. Attempting to make it writeable'.format
                         (name=filename))
            try:
                os.chmod(filename, stat.S_IWRITE)
            except:
                logger.warning('Cannot change permissions of {file}'.format(file=filename), logger.WARNING)


# Wake function
def WakeOnLan(ethernet_address):
    addr_byte = ethernet_address.split(':')
    hw_addr = struct.pack(b'BBBBBB', int(addr_byte[0], 16),
                          int(addr_byte[1], 16),
                          int(addr_byte[2], 16),
                          int(addr_byte[3], 16),
                          int(addr_byte[4], 16),
                          int(addr_byte[5], 16))

    # Build the Wake-On-LAN "Magic Packet"...

    msg = b'\xff' * 6 + hw_addr * 16

    # ...and send it to the broadcast address using UDP

    ss = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ss.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    ss.sendto(msg, ('<broadcast>', 9))
    ss.close()


# Test Connection function
def TestCon(host, port):
    try:
        socket.create_connection((host, port))
        return "Up"
    except:
        return "Down"


def WakeUp():
    host = core.CFG["WakeOnLan"]["host"]
    port = int(core.CFG["WakeOnLan"]["port"])
    mac = core.CFG["WakeOnLan"]["mac"]

    i = 1
    while TestCon(host, port) == "Down" and i < 4:
        logger.info(("Sending WakeOnLan Magic Packet for mac: {0}".format(mac)))
        WakeOnLan(mac)
        time.sleep(20)
        i = i + 1

    if TestCon(host, port) == "Down":  # final check.
        logger.warning("System with mac: {0} has not woken after 3 attempts. "
                       "Continuing with the rest of the script.".format(mac))
    else:
        logger.info("System with mac: {0} has been woken. Continuing with the rest of the script.".format(mac))


def CharReplace(Name):
    # Special character hex range:
    # CP850: 0x80-0xA5 (fortunately not used in ISO-8859-15)
    # UTF-8: 1st hex code 0xC2-0xC3 followed by a 2nd hex code 0xA1-0xFF
    # ISO-8859-15: 0xA6-0xFF
    # The function will detect if Name contains a special character
    # If there is special character, detects if it is a UTF-8, CP850 or ISO-8859-15 encoding
    encoded = False
    encoding = None
    if isinstance(Name, unicode):
        return encoded, Name.encode(core.SYS_ENCODING)
    for Idx in range(len(Name)):
        # /!\ detection is done 2char by 2char for UTF-8 special character
        if (len(Name) != 1) & (Idx < (len(Name) - 1)):
            # Detect UTF-8
            if ((Name[Idx] == '\xC2') | (Name[Idx] == '\xC3')) & (
                        (Name[Idx + 1] >= '\xA0') & (Name[Idx + 1] <= '\xFF')):
                encoding = 'utf-8'
                break
            # Detect CP850
            elif (Name[Idx] >= '\x80') & (Name[Idx] <= '\xA5'):
                encoding = 'cp850'
                break
            # Detect ISO-8859-15
            elif (Name[Idx] >= '\xA6') & (Name[Idx] <= '\xFF'):
                encoding = 'iso-8859-15'
                break
        else:
            # Detect CP850
            if (Name[Idx] >= '\x80') & (Name[Idx] <= '\xA5'):
                encoding = 'cp850'
                break
            # Detect ISO-8859-15
            elif (Name[Idx] >= '\xA6') & (Name[Idx] <= '\xFF'):
                encoding = 'iso-8859-15'
                break
    if encoding and not encoding == core.SYS_ENCODING:
        encoded = True
        Name = Name.decode(encoding).encode(core.SYS_ENCODING)
    return encoded, Name


def convert_to_ascii(inputName, dirName):
    ascii_convert = int(core.CFG["ASCII"]["convert"])
    if ascii_convert == 0 or os.name == 'nt':  # just return if we don't want to convert or on windows os and "\" is replaced!.
        return inputName, dirName

    encoded, inputName = CharReplace(inputName)

    dir, base = os.path.split(dirName)
    if not base:  # ended with "/"
        dir, base = os.path.split(dir)

    encoded, base2 = CharReplace(base)
    if encoded:
        dirName = os.path.join(dir, base2)
        logger.info("Renaming directory to: {0}.".format(base2), 'ENCODER')
        os.rename(os.path.join(dir, base), dirName)
        if 'NZBOP_SCRIPTDIR' in os.environ:
            print("[NZB] DIRECTORY={0}".format(dirName))

    for dirname, dirnames, filenames in os.walk(dirName, topdown=False):
        for subdirname in dirnames:
            encoded, subdirname2 = CharReplace(subdirname)
            if encoded:
                logger.info("Renaming directory to: {0}.".format(subdirname2), 'ENCODER')
                os.rename(os.path.join(dirname, subdirname), os.path.join(dirname, subdirname2))

    for dirname, dirnames, filenames in os.walk(dirName):
        for filename in filenames:
            encoded, filename2 = CharReplace(filename)
            if encoded:
                logger.info("Renaming file to: {0}.".format(filename2), 'ENCODER')
                os.rename(os.path.join(dirname, filename), os.path.join(dirname, filename2))

    return inputName, dirName


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
    inputHash = args[1]
    inputID = args[1]
    try:
        inputCategory = core.TORRENT_CLASS.core.get_torrent_status(inputID, ['label']).get()['label']
    except:
        inputCategory = ''
    return inputDirectory, inputName, inputCategory, inputHash, inputID


def parse_transmission(args):
    # Transmission usage: call TorrenToMedia.py (%TR_TORRENT_DIR% %TR_TORRENT_NAME% is passed on as environmental variables)
    inputDirectory = os.path.normpath(os.getenv('TR_TORRENT_DIR'))
    inputName = os.getenv('TR_TORRENT_NAME')
    inputCategory = ''  # We dont have a category yet
    inputHash = os.getenv('TR_TORRENT_HASH')
    inputID = os.getenv('TR_TORRENT_ID')
    return inputDirectory, inputName, inputCategory, inputHash, inputID


def parse_vuze(args):
    # vuze usage: C:\full\path\to\nzbToMedia\TorrentToMedia.py "%D%N%L%I%K%F"
    try:
        input = args[1].split(',')
    except:
        input = []
    try:
        inputDirectory = os.path.normpath(input[0])
    except:
        inputDirectory = ''
    try:
        inputName = input[1]
    except:
        inputName = ''
    try:
        inputCategory = input[2]
    except:
        inputCategory = ''
    try:
        inputHash = input[3]
    except:
        inputHash = ''
    try:
        inputID = input[3]
    except:
        inputID = ''
    try:
        if input[4] == 'single':
            inputName = input[5]
    except:
        pass

    return inputDirectory, inputName, inputCategory, inputHash, inputID

def parse_qbittorrent(args):
    # qbittorrent usage: C:\full\path\to\nzbToMedia\TorrentToMedia.py "%D|%N|%L|%I"
    try:
        input = args[1].split('|')
    except:
        input = []
    try:
        inputDirectory = os.path.normpath(input[0].replace('"',''))
    except:
        inputDirectory = ''
    try:
        inputName = input[1].replace('"','')
    except:
        inputName = ''
    try:
        inputCategory = input[2].replace('"','')
    except:
        inputCategory = ''
    try:
        inputHash = input[3].replace('"','')
    except:
        inputHash = ''
    try:
        inputID = input[3].replace('"','')
    except:
        inputID = ''

    return inputDirectory, inputName, inputCategory, inputHash, inputID

def parse_args(clientAgent, args):
    clients = {
        'other': parse_other,
        'rtorrent': parse_rtorrent,
        'utorrent': parse_utorrent,
        'deluge': parse_deluge,
        'transmission': parse_transmission,
        'qbittorrent': parse_qbittorrent,
        'vuze': parse_vuze,
    }

    try:
        return clients[clientAgent](args)
    except:
        return None, None, None, None, None


def getDirs(section, subsection, link='hard'):
    to_return = []

    def processDir(path):
        folders = []

        logger.info("Searching {0} for mediafiles to post-process ...".format(path))
        sync = [o for o in os.listdir(unicode(path)) if os.path.splitext(o)[1] in ['.!sync', '.bts']]
        # search for single files and move them into their own folder for post-processing
        for mediafile in [os.path.join(path, o) for o in os.listdir(unicode(path)) if
                          os.path.isfile(os.path.join(path, o))]:
            if len(sync) > 0:
                break
            if os.path.split(mediafile)[1] in ['Thumbs.db', 'thumbs.db']:
                continue
            try:
                logger.debug("Found file {0} in root directory {1}.".format(os.path.split(mediafile)[1], path))
                newPath = None
                fileExt = os.path.splitext(mediafile)[1]
                try:
                    if fileExt in core.AUDIOCONTAINER:
                        f = beets.mediafile.MediaFile(mediafile)

                        # get artist and album info
                        artist = f.artist
                        album = f.album

                        # create new path
                        newPath = os.path.join(path, "{0} - {1}".format(sanitizeName(artist), sanitizeName(album)))
                    elif fileExt in core.MEDIACONTAINER:
                        f = guessit.guessit(mediafile)

                        # get title
                        title = f.get('series') or f.get('title')

                        if not title:
                            title = os.path.splitext(os.path.basename(mediafile))[0]

                        newPath = os.path.join(path, sanitizeName(title))
                except Exception as e:
                    logger.error("Exception parsing name for media file: {0}: {1}".format(os.path.split(mediafile)[1], e))

                if not newPath:
                    title = os.path.splitext(os.path.basename(mediafile))[0]
                    newPath = os.path.join(path, sanitizeName(title))

                try:
                    newPath = newPath.encode(core.SYS_ENCODING)
                except:
                    pass

                # Just fail-safe incase we already have afile with this clean-name (was actually a bug from earlier code, but let's be safe).
                if os.path.isfile(newPath):
                    newPath2 = os.path.join(os.path.join(os.path.split(newPath)[0], 'new'), os.path.split(newPath)[1])
                    newPath = newPath2

                # create new path if it does not exist
                if not os.path.exists(newPath):
                    makeDir(newPath)

                newfile = os.path.join(newPath, sanitizeName(os.path.split(mediafile)[1]))
                try:
                    newfile = newfile.encode(core.SYS_ENCODING)
                except:
                    pass

                # link file to its new path
                copy_link(mediafile, newfile, link)
            except Exception as e:
                logger.error("Failed to move {0} to its own directory: {1}".format(os.path.split(mediafile)[1], e))

        # removeEmptyFolders(path, removeRoot=False)

        if os.listdir(unicode(path)):
            for dir in [os.path.join(path, o) for o in os.listdir(unicode(path)) if
                        os.path.isdir(os.path.join(path, o))]:
                sync = [o for o in os.listdir(unicode(dir)) if os.path.splitext(o)[1] in ['.!sync', '.bts']]
                if len(sync) > 0 or len(os.listdir(unicode(dir))) == 0:
                    continue
                folders.extend([dir])
        return folders

    try:
        watch_dir = os.path.join(core.CFG[section][subsection]["watch_dir"], subsection)
        if os.path.exists(watch_dir):
            to_return.extend(processDir(watch_dir))
        elif os.path.exists(core.CFG[section][subsection]["watch_dir"]):
            to_return.extend(processDir(core.CFG[section][subsection]["watch_dir"]))
    except Exception as e:
        logger.error("Failed to add directories from {0} for post-processing: {1}".format
                     (core.CFG[section][subsection]["watch_dir"], e))

    if core.USELINK == 'move':
        try:
            outputDirectory = os.path.join(core.OUTPUTDIRECTORY, subsection)
            if os.path.exists(outputDirectory):
                to_return.extend(processDir(outputDirectory))
        except Exception as e:
            logger.error("Failed to add directories from {0} for post-processing: {1}".format(core.OUTPUTDIRECTORY, e))

    if not to_return:
        logger.debug("No directories identified in {0}:{1} for post-processing".format(section, subsection))

    return list(set(to_return))


def onerror(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.
    
    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    if not os.access(path, os.W_OK):
        # Is the error an access error ?
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise Exception


def rmDir(dirName):
    logger.info("Deleting {0}".format(dirName))
    try:
        shutil.rmtree(unicode(dirName), onerror=onerror)
    except:
        logger.error("Unable to delete folder {0}".format(dirName))


def cleanDir(path, section, subsection):
    cfg = dict(core.CFG[section][subsection])
    if not os.path.exists(path):
        logger.info('Directory {0} has been processed and removed ...'.format(path), 'CLEANDIR')
        return
    if core.FORCE_CLEAN and not core.FAILED:
        logger.info('Doing Forceful Clean of {0}'.format(path), 'CLEANDIR')
        rmDir(path)
        return
    minSize = int(cfg.get('minSize', 0))
    delete_ignored = int(cfg.get('delete_ignored', 0))
    try:
        num_files = len(listMediaFiles(path, minSize=minSize, delete_ignored=delete_ignored))
    except:
        num_files = 'unknown'
    if num_files > 0:
        logger.info(
            "Directory {0} still contains {1} unprocessed file(s), skipping ...".format(path, num_files),
            'CLEANDIRS')
        return

    logger.info("Directory {0} has been processed, removing ...".format(path), 'CLEANDIRS')
    try:
        shutil.rmtree(path, onerror=onerror)
    except:
        logger.error("Unable to delete directory {0}".format(path))


def create_torrent_class(clientAgent):
    # Hardlink solution for Torrents
    tc = None

    if clientAgent == 'utorrent':
        try:
            logger.debug("Connecting to {0}: {1}".format(clientAgent, core.UTORRENTWEBUI))
            tc = UTorrentClient(core.UTORRENTWEBUI, core.UTORRENTUSR, core.UTORRENTPWD)
        except:
            logger.error("Failed to connect to uTorrent")

    if clientAgent == 'transmission':
        try:
            logger.debug("Connecting to {0}: http://{1}:{2}".format(
                clientAgent, core.TRANSMISSIONHOST, core.TRANSMISSIONPORT))
            tc = TransmissionClient(core.TRANSMISSIONHOST, core.TRANSMISSIONPORT,
                                    core.TRANSMISSIONUSR,
                                    core.TRANSMISSIONPWD)
        except:
            logger.error("Failed to connect to Transmission")

    if clientAgent == 'deluge':
        try:
            logger.debug("Connecting to {0}: http://{1}:{2}".format(clientAgent, core.DELUGEHOST, core.DELUGEPORT))
            tc = DelugeClient()
            tc.connect(host=core.DELUGEHOST, port=core.DELUGEPORT, username=core.DELUGEUSR,
                       password=core.DELUGEPWD)
        except:
            logger.error("Failed to connect to Deluge")

    if clientAgent == 'qbittorrent':
        try:
            logger.debug("Connecting to {0}: http://{1}:{2}".format(clientAgent, core.QBITTORRENTHOST, core.QBITTORRENTPORT))
            tc = qBittorrentClient("http://{0}:{1}/".format(core.QBITTORRENTHOST, core.QBITTORRENTPORT))
            tc.login(core.QBITTORRENTUSR, core.QBITTORRENTPWD)
        except:
            logger.error("Failed to connect to qBittorrent")

    return tc


def pause_torrent(clientAgent, inputHash, inputID, inputName):
    logger.debug("Stopping torrent {0} in {1} while processing".format(inputName, clientAgent))
    try:
        if clientAgent == 'utorrent' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.stop(inputHash)
        if clientAgent == 'transmission' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.stop_torrent(inputID)
        if clientAgent == 'deluge' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.core.pause_torrent([inputID])
        if clientAgent == 'qbittorrent' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.pause(inputHash)
        time.sleep(5)
    except:
        logger.warning("Failed to stop torrent {0} in {1}".format(inputName, clientAgent))


def resume_torrent(clientAgent, inputHash, inputID, inputName):
    if not core.TORRENT_RESUME == 1:
        return
    logger.debug("Starting torrent {0} in {1}".format(inputName, clientAgent))
    try:
        if clientAgent == 'utorrent' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.start(inputHash)
        if clientAgent == 'transmission' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.start_torrent(inputID)
        if clientAgent == 'deluge' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.core.resume_torrent([inputID])
        if clientAgent == 'qbittorrent' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.resume(inputHash)
        time.sleep(5)
    except:
        logger.warning("Failed to start torrent {0} in {1}".format(inputName, clientAgent))


def remove_torrent(clientAgent, inputHash, inputID, inputName):
    if core.DELETE_ORIGINAL == 1 or core.USELINK == 'move':
        logger.debug("Deleting torrent {0} from {1}".format(inputName, clientAgent))
        try:
            if clientAgent == 'utorrent' and core.TORRENT_CLASS != "":
                core.TORRENT_CLASS.removedata(inputHash)
                core.TORRENT_CLASS.remove(inputHash)
            if clientAgent == 'transmission' and core.TORRENT_CLASS != "":
                core.TORRENT_CLASS.remove_torrent(inputID, True)
            if clientAgent == 'deluge' and core.TORRENT_CLASS != "":
                core.TORRENT_CLASS.core.remove_torrent(inputID, True)
            if clientAgent == 'qbittorrent' and core.TORRENT_CLASS != "":
                core.TORRENT_CLASS.delete_permanently(inputHash)
            time.sleep(5)
        except:
            logger.warning("Failed to delete torrent {0} in {1}".format(inputName, clientAgent))
    else:
        resume_torrent(clientAgent, inputHash, inputID, inputName)


def find_download(clientAgent, download_id):
    logger.debug("Searching for Download on {0} ...".format(clientAgent))
    if clientAgent == 'utorrent':
        torrents = core.TORRENT_CLASS.list()[1]['torrents']
        for torrent in torrents:
            if download_id in torrent:
                return True
    if clientAgent == 'transmission':
        torrents = core.TORRENT_CLASS.get_torrents()
        for torrent in torrents:
            hash = torrent.hashString
            if hash == download_id:
                return True
    if clientAgent == 'deluge':
        return False
    if clientAgent == 'qbittorrent':
        torrents = core.TORRENT_CLASS.torrents()
        for torrent in torrents:
            if torrent['hash'] == download_id:
                return True
    if clientAgent == 'sabnzbd':
        if "http" in core.SABNZBDHOST:
            baseURL = "{0}:{1}/api".format(core.SABNZBDHOST, core.SABNZBDPORT)
        else:
            baseURL = "http://{0}:{1}/api".format(core.SABNZBDHOST, core.SABNZBDPORT)
        url = baseURL
        params = {
            'apikey': core.SABNZBDAPIKEY,
            'mode': "get_files",
            'output': 'json',
            'value': download_id,
        }
        try:
            r = requests.get(url, params=params, verify=False, timeout=(30, 120))
        except requests.ConnectionError:
            logger.error("Unable to open URL")
            return False  # failure

        result = r.json()
        if result['files']:
            return True
    return False


def get_nzoid(inputName):
    nzoid = None
    slots = []
    logger.debug("Searching for nzoid from SAbnzbd ...")
    if "http" in core.SABNZBDHOST:
        baseURL = "{0}:{1}/api".format(core.SABNZBDHOST, core.SABNZBDPORT)
    else:
        baseURL = "http://{0}:{1}/api".format(core.SABNZBDHOST, core.SABNZBDPORT)
    url = baseURL
    params = {
        'apikey': core.SABNZBDAPIKEY,
        'mode': "queue",
        'output': 'json',
    }
    try:
        r = requests.get(url, params=params, verify=False, timeout=(30, 120))
    except requests.ConnectionError:
        logger.error("Unable to open URL")
        return nzoid  # failure
    try:
        result = r.json()
        cleanName = os.path.splitext(os.path.split(inputName)[1])[0]
        slots.extend([(slot['nzo_id'], slot['filename']) for slot in result['queue']['slots']])
    except:
        logger.warning("Data from SABnzbd queue could not be parsed")
    params['mode'] = "history"
    try:
        r = requests.get(url, params=params, verify=False, timeout=(30, 120))
    except requests.ConnectionError:
        logger.error("Unable to open URL")
        return nzoid  # failure
    try:
        result = r.json()
        cleanName = os.path.splitext(os.path.split(inputName)[1])[0]
        slots.extend([(slot['nzo_id'], slot['name']) for slot in result['history']['slots']])
    except:
        logger.warning("Data from SABnzbd history could not be parsed")
    try:
        for nzo_id, name in slots:
            if name in [inputName, cleanName]:
                nzoid = nzo_id
                logger.debug("Found nzoid: {0}".format(nzoid))
                break
    except:
        logger.warning("Data from SABnzbd could not be parsed")
    return nzoid


def cleanFileName(filename):
    """Cleans up nzb name by removing any . and _
    characters, along with any trailing hyphens.

    Is basically equivalent to replacing all _ and . with a
    space, but handles decimal numbers in string, for example:
    """

    filename = re.sub("(\D)\.(?!\s)(\D)", "\\1 \\2", filename)
    filename = re.sub("(\d)\.(\d{4})", "\\1 \\2", filename)  # if it ends in a year then don't keep the dot
    filename = re.sub("(\D)\.(?!\s)", "\\1 ", filename)
    filename = re.sub("\.(?!\s)(\D)", " \\1", filename)
    filename = filename.replace("_", " ")
    filename = re.sub("-$", "", filename)
    filename = re.sub("^\[.*\]", "", filename)
    return filename.strip()


def is_archive_file(filename):
    """Check if the filename is allowed for the Archive"""
    for regext in core.COMPRESSEDCONTAINER:
        if regext.search(filename):
            return regext.split(filename)[0]
    return False


def isMediaFile(mediafile, media=True, audio=True, meta=True, archives=True, other=False, otherext=[]):
    fileName, fileExt = os.path.splitext(mediafile)

    try:
        # ignore MAC OS's "resource fork" files
        if fileName.startswith('._'):
            return False
    except:
        pass
    if (media and fileExt.lower() in core.MEDIACONTAINER) \
            or (audio and fileExt.lower() in core.AUDIOCONTAINER) \
            or (meta and fileExt.lower() in core.METACONTAINER) \
            or (archives and is_archive_file(mediafile)) \
            or (other and (fileExt.lower() in otherext or 'all' in otherext)):
        return True
    else:
        return False


def listMediaFiles(path, minSize=0, delete_ignored=0, media=True, audio=True, meta=True, archives=True, other=False, otherext=[]):
    files = []
    if not os.path.isdir(path):
        if os.path.isfile(path):  # Single file downloads.
            curFile = os.path.split(path)[1]
            if isMediaFile(curFile, media, audio, meta, archives, other, otherext):
                # Optionally ignore sample files
                if is_sample(path) or not is_minSize(path, minSize):
                    if delete_ignored == 1:
                        try:
                            os.unlink(path)
                            logger.debug('Ignored file {0} has been removed ...'.format
                                         (curFile))
                        except:
                            pass
                else:
                    files.append(path)

        return files

    for curFile in os.listdir(unicode(path)):
        fullCurFile = os.path.join(path, curFile)

        # if it's a folder do it recursively
        if os.path.isdir(fullCurFile) and not curFile.startswith('.'):
            files += listMediaFiles(fullCurFile, minSize, delete_ignored, media, audio, meta, archives, other, otherext)

        elif isMediaFile(curFile, media, audio, meta, archives, other, otherext):
            # Optionally ignore sample files
            if is_sample(fullCurFile) or not is_minSize(fullCurFile, minSize):
                if delete_ignored == 1:
                    try:
                        os.unlink(fullCurFile)
                        logger.debug('Ignored file {0} has been removed ...'.format
                                     (curFile))
                    except:
                        pass
                continue

            files.append(fullCurFile)

    return sorted(files, key=len)


def find_imdbid(dirName, inputName, omdbApiKey):
    imdbid = None

    logger.info('Attemping imdbID lookup for {0}'.format(inputName))

    # find imdbid in dirName
    logger.info('Searching folder and file names for imdbID ...')
    m = re.search('(tt\d{7})', dirName + inputName)
    if m:
        imdbid = m.group(1)
        logger.info("Found imdbID [{0}]".format(imdbid))
        return imdbid
    if os.path.isdir(dirName):
        for file in os.listdir(unicode(dirName)):
            m = re.search('(tt\d{7})', file)
            if m:
                imdbid = m.group(1)
                logger.info("Found imdbID [{0}] via file name".format(imdbid))
                return imdbid
    if 'NZBPR__DNZB_MOREINFO' in os.environ:
        dnzb_more_info = os.environ.get('NZBPR__DNZB_MOREINFO', '')
        if dnzb_more_info != '':
            regex = re.compile(r'^http://www.imdb.com/title/(tt[0-9]+)/$', re.IGNORECASE)
            m = regex.match(dnzb_more_info)
            if m:
                imdbid = m.group(1)
                logger.info("Found imdbID [{0}] from DNZB-MoreInfo".format(imdbid))
                return imdbid
    logger.info('Searching IMDB for imdbID ...')
    try:
        guess = guessit.guessit(inputName)
    except:
        guess = None
    if guess:
        # Movie Title
        title = None
        if 'title' in guess:
            title = guess['title']

        # Movie Year
        year = None
        if 'year' in guess:
            year = guess['year']

        url = "http://www.omdbapi.com"

        if not omdbApiKey:
            logger.info("Unable to determine imdbID: No api key provided for ombdapi.com.")
            return

        logger.debug("Opening URL: {0}".format(url))

        try:
            r = requests.get(url, params={'apikey': omdbApiKey, 'y': year, 't': title},
            verify=False, timeout=(60, 300))
        except requests.ConnectionError:
            logger.error("Unable to open URL {0}".format(url))
            return

        try:
            results = r.json()
        except:
            logger.error("No json data returned from omdbapi.com")

        try:
            imdbid = results['imdbID']
        except:
            logger.error("No imdbID returned from omdbapi.com")

        if imdbid:
            logger.info("Found imdbID [{0}]".format(imdbid))
            return imdbid

    logger.warning('Unable to find a imdbID for {0}'.format(inputName))
    return imdbid


def extractFiles(src, dst=None, keep_archive=None):
    extracted_folder = []
    extracted_archive = []

    for inputFile in listMediaFiles(src, media=False, audio=False, meta=False, archives=True):
        dirPath = os.path.dirname(inputFile)
        fullFileName = os.path.basename(inputFile)
        archiveName = os.path.splitext(fullFileName)[0]
        archiveName = re.sub(r"part[0-9]+", "", archiveName)

        if dirPath in extracted_folder and archiveName in extracted_archive:
            continue  # no need to extract this, but keep going to look for other archives and sub directories.

        try:
            if extractor.extract(inputFile, dst or dirPath):
                extracted_folder.append(dirPath)
                extracted_archive.append(archiveName)
        except Exception:
            logger.error("Extraction failed for: {0}".format(fullFileName))

    for folder in extracted_folder:
        for inputFile in listMediaFiles(folder, media=False, audio=False, meta=False, archives=True):
            fullFileName = os.path.basename(inputFile)
            archiveName = os.path.splitext(fullFileName)[0]
            archiveName = re.sub(r"part[0-9]+", "", archiveName)
            if archiveName not in extracted_archive or keep_archive:
                continue  # don't remove if we haven't extracted this archive, or if we want to preserve them.
            logger.info("Removing extracted archive {0} from folder {1} ...".format(fullFileName, folder))
            try:
                if not os.access(inputFile, os.W_OK):
                    os.chmod(inputFile, stat.S_IWUSR)
                os.remove(inputFile)
                time.sleep(1)
            except Exception as e:
                logger.error("Unable to remove file {0} due to: {1}".format(inputFile, e))


def import_subs(filename):
    if not core.GETSUBS:
        return
    try:
        subliminal.region.configure('dogpile.cache.dbm', arguments={'filename': 'cachefile.dbm'})
    except:
        pass

    languages = set()
    for item in core.SLANGUAGES:
        try:
            languages.add(Language(item))
        except:
            pass
    if not languages:
        return

    logger.info("Attempting to download subtitles for {0}".format(filename), 'SUBTITLES')
    try:
        video = subliminal.scan_video(filename)
        subtitles = subliminal.download_best_subtitles({video}, languages)
        subliminal.save_subtitles(video, subtitles[video])
    except Exception as e:
        logger.error("Failed to download subtitles for {0} due to: {1}".format(filename, e), 'SUBTITLES')


def server_responding(baseURL):
    logger.debug("Attempting to connect to server at {0}".format(baseURL), 'SERVER')
    try:
        requests.get(baseURL, timeout=(60, 120), verify=False)
        logger.debug("Server responded at {0}".format(baseURL), 'SERVER')
        return True
    except (requests.ConnectionError, requests.exceptions.Timeout):
        logger.error("Server failed to respond at {0}".format(baseURL), 'SERVER')
        return False


def plex_update(category):
    if core.FAILED:
        return
    url = '{scheme}://{host}:{port}/library/sections/'.format(
        scheme='https' if core.PLEXSSL else 'http',
        host=core.PLEXHOST,
        port=core.PLEXPORT,
    )
    section = None
    if not core.PLEXSEC:
        return
    logger.debug("Attempting to update Plex Library for category {0}.".format(category), 'PLEX')
    for item in core.PLEXSEC:
        if item[0] == category:
            section = item[1]

    if section:
        url = '{url}{section}/refresh?X-Plex-Token={token}'.format(url=url, section=section, token=core.PLEXTOKEN)
        requests.get(url, timeout=(60, 120), verify=False)
        logger.debug("Plex Library has been refreshed.", 'PLEX')
    else:
        logger.debug("Could not identify section for plex update", 'PLEX')


def backupVersionedFile(old_file, version):
    numTries = 0

    new_file = '{old}.v{version}'.format(old=old_file, version=version)

    while not os.path.isfile(new_file):
        if not os.path.isfile(old_file):
            logger.log(u"Not creating backup, {file} doesn't exist".format(file=old_file), logger.DEBUG)
            break

        try:
            logger.log(u"Trying to back up {old} to {new]".format(old=old_file, new=new_file), logger.DEBUG)
            shutil.copy(old_file, new_file)
            logger.log(u"Backup done", logger.DEBUG)
            break
        except Exception as error:
            logger.log(u"Error while trying to back up {old} to {new} : {msg}".format
                       (old=old_file, new=new_file, msg=error), logger.WARNING)
            numTries += 1
            time.sleep(1)
            logger.log(u"Trying again.", logger.DEBUG)

        if numTries >= 10:
            logger.log(u"Unable to back up {old} to {new} please do it manually.".format(old=old_file, new=new_file), logger.ERROR)
            return False

    return True


def update_downloadInfoStatus(inputName, status):
    logger.db("Updating status of our download {0} in the DB to {1}".format(inputName, status))

    myDB = nzbToMediaDB.DBConnection()
    myDB.action("UPDATE downloads SET status=?, last_update=? WHERE input_name=?",
                [status, datetime.date.today().toordinal(), text_type(inputName)])


def get_downloadInfo(inputName, status):
    logger.db("Getting download info for {0} from the DB".format(inputName))

    myDB = nzbToMediaDB.DBConnection()
    sqlResults = myDB.select("SELECT * FROM downloads WHERE input_name=? AND status=?",
                             [text_type(inputName), status])

    return sqlResults


class RunningProcess(object):
    """ Limits application to single instance """

    def __init__(self):
        if platform.system() == 'Windows':
            self.process = WindowsProcess()
        else:
            self.process = PosixProcess()

    def alreadyrunning(self):
        return self.process.alreadyrunning()

        # def __del__(self):
        #    self.process.__del__()


class WindowsProcess(object):
    def __init__(self):
        self.mutexname = "nzbtomedia_{pid}".format(pid=core.PID_FILE.replace('\\', '/'))  # {D0E858DF-985E-4907-B7FB-8D732C3FC3B9}"
        if platform.system() == 'Windows':
            from win32event import CreateMutex
            from win32api import CloseHandle, GetLastError
            from winerror import ERROR_ALREADY_EXISTS
            self.CreateMutex = CreateMutex
            self.CloseHandle = CloseHandle
            self.GetLastError = GetLastError
            self.ERROR_ALREADY_EXISTS = ERROR_ALREADY_EXISTS

    def alreadyrunning(self):
        self.mutex = self.CreateMutex(None, 0, self.mutexname)
        self.lasterror = self.GetLastError()
        if self.lasterror == self.ERROR_ALREADY_EXISTS:
            self.CloseHandle(self.mutex)
            return True
        else:
            return False

    def __del__(self):
        if self.mutex:
            self.CloseHandle(self.mutex)


class PosixProcess(object):
    def __init__(self):
        self.pidpath = core.PID_FILE
        self.lock_socket = None

    def alreadyrunning(self):
        try:
            self.lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.lock_socket.bind('\0{path}'.format(path=self.pidpath))
            self.lasterror = False
            return self.lasterror
        except socket.error as e:
            if "Address already in use" in e:
                self.lasterror = True
                return self.lasterror
        except AttributeError:
            pass
        if os.path.exists(self.pidpath):
            # Make sure it is not a "stale" pidFile
            try:
                pid = int(open(self.pidpath, 'r').read().strip())
            except:
                pid = None
            # Check list of running pids, if not running it is stale so overwrite
            if isinstance(pid, int):
                try:
                    os.kill(pid, 0)
                    self.lasterror = True
                except OSError:
                    self.lasterror = False
            else:
                self.lasterror = False
        else:
            self.lasterror = False

        if not self.lasterror:
            # Write my pid into pidFile to keep multiple copies of program from running
            try:
                fp = open(self.pidpath, 'w')
                fp.write(str(os.getpid()))
                fp.close()
            except:
                pass

        return self.lasterror

    def __del__(self):
        if not self.lasterror:
            if self.lock_socket:
                self.lock_socket.close()
            if os.path.isfile(self.pidpath):
                os.unlink(self.pidpath)
