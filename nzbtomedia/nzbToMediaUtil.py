import os
import re
import socket
import stat
import struct
import shutil
import time
import datetime
import guessit
import beets
import requests
import nzbtomedia

from nzbtomedia.extractor import extractor
from nzbtomedia.linktastic import linktastic
from nzbtomedia.synchronousdeluge.client import DelugeClient
from nzbtomedia.utorrent.client import UTorrentClient
from nzbtomedia.transmissionrpc.client import Client as TransmissionClient
from nzbtomedia import logger, nzbToMediaDB

def sanitizeName(name):
    '''
    >>> sanitizeName('a/b/c')
    'a-b-c'
    >>> sanitizeName('abc')
    'abc'
    >>> sanitizeName('a"b')
    'ab'
    >>> sanitizeName('.a.b..')
    'a.b'
    '''

    # remove bad chars from the filename
    name = re.sub(r'[\\/\*]', '-', name)
    name = re.sub(r'[:"<>|?]', '', name)

    # remove leading/trailing periods and spaces
    name = name.strip(' .')

    return name

def makeDir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except Exception, e:
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
        logger.debug("SEARCH: Found Category: %s in directory structure" % (inputCategory))
    except IndexError:
        inputCategory = ""
        logger.debug("SEARCH: Could not find a category in the directory structure")

    if not os.path.isdir(inputDirectory) and os.path.isfile(inputDirectory):  # If the input directory is a file
        single = True
        if not inputName: inputName = os.path.split(os.path.normpath(inputDirectory))[1]
        return inputDirectory, inputName, inputCategory, root, single

    if inputCategory and os.path.isdir(os.path.join(inputDirectory, inputCategory)):
        logger.info(
            "SEARCH: Found category directory %s in input directory directory %s" % (inputCategory, inputDirectory))
        inputDirectory = os.path.join(inputDirectory, inputCategory)
        logger.info("SEARCH: Setting inputDirectory to %s" % (inputDirectory))
    if inputName and os.path.isdir(os.path.join(inputDirectory, inputName)):
        logger.info("SEARCH: Found torrent directory %s in input directory directory %s" % (inputName, inputDirectory))
        inputDirectory = os.path.join(inputDirectory, inputName)
        logger.info("SEARCH: Setting inputDirectory to %s" % (inputDirectory))
        tordir = True
    if inputName and os.path.isdir(os.path.join(inputDirectory, sanitizeName(inputName))):
        logger.info("SEARCH: Found torrent directory %s in input directory directory %s" % (
            sanitizeName(inputName), inputDirectory))
        inputDirectory = os.path.join(inputDirectory, sanitizeName(inputName))
        logger.info("SEARCH: Setting inputDirectory to %s" % (inputDirectory))
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
                logger.info("SEARCH: Found a unique directory %s in the category directory" % (pathlist[index + 1]))
                if not inputName: inputName = pathlist[index + 1]
        except ValueError:
            pass

    if inputName and not tordir:
        if inputName in pathlist or sanitizeName(inputName) in pathlist:
            logger.info("SEARCH: Found torrent directory %s in the directory structure" % (inputName))
            tordir = True
        else:
            root = 1
    if not tordir:
        root = 2

    if root > 0:
        logger.info("SEARCH: Could not find a unique directory for this download. Assume a common directory.")
        logger.info("SEARCH: We will try and determine which files to process, individually")

    return inputDirectory, inputName, inputCategory, root, single

def getDirSize(inputPath):
   from functools import partial
   prepend = partial(os.path.join, inputPath)
   return sum([(os.path.getsize(f) if os.path.isfile(f) else getDirSize(f)) for f in map(prepend, os.listdir(inputPath))])

def is_minSize(inputName, minSize):
    fileName, fileExt = os.path.splitext(os.path.basename(inputName))


    # audio files we need to check directory size not file size
    inputSize = os.path.getsize(inputName)
    if fileExt in (nzbtomedia.AUDIOCONTAINER):
        inputSize = getDirSize(os.path.dirname(inputName))

    # Ignore files under a certain size
    if inputSize > minSize * 1048576:
        return True

def is_sample(inputName):
    # Ignore 'sample' in files
    if re.search('(^|[\W_])sample\d*[\W_]', inputName.lower()):
        return True

def copy_link(src, targetLink, useLink):
    logger.info("MEDIAFILE: [%s]" % (os.path.basename(targetLink)), 'COPYLINK')
    logger.info("SOURCE FOLDER: [%s]" % (os.path.dirname(src)), 'COPYLINK')
    logger.info("TARGET FOLDER: [%s]" % (os.path.dirname(targetLink)), 'COPYLINK')

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
            shutil.move(src, targetLink)
            linktastic.symlink(targetLink, src)
            return True
        elif useLink == "move":
            logger.info("Moving SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
            shutil.move(src, targetLink)
            return True
    except Exception, e:
        logger.warning("Error: %s, copying instead ... " % (e), 'COPYLINK')

    logger.info("Copying SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
    shutil.copy(src, targetLink)

    return True

def flatten(outputDestination):
    logger.info("FLATTEN: Flattening directory: %s" % (outputDestination))
    for outputFile in listMediaFiles(outputDestination):
        dirPath = os.path.dirname(outputFile)
        fileName = os.path.basename(outputFile)

        if dirPath == outputDestination:
            continue

        target = os.path.join(outputDestination, fileName)

        try:
            shutil.move(outputFile, target)
        except:
            logger.error("Could not flatten %s" % (outputFile), 'FLATTEN')

    removeEmptyFolders(outputDestination)  # Cleanup empty directories

def removeEmptyFolders(path, removeRoot=True):
  'Function to remove empty folders'
  if not os.path.isdir(path):
    return

  # remove empty subfolders
  logger.debug("Checking for empty folders in:%s" % (path))
  files = os.listdir(path)
  if len(files):
    for f in files:
      fullpath = os.path.join(path, f)
      if os.path.isdir(fullpath):
        removeEmptyFolders(fullpath)

  # if folder empty, delete it
  files = os.listdir(path)
  if len(files) == 0 and removeRoot:
    logger.debug("Removing empty folder:%s" % (path))
    os.rmdir(path)

def rmReadOnly(filename):
    if os.path.isfile(filename):
        #check first the read-only attribute
        file_attribute = os.stat(filename)[0]
        if (not file_attribute & stat.S_IWRITE):
            # File is read-only, so make it writeable
            logger.debug('Read only mode on file ' + filename + ' Will try to make it writeable')
            try:
                os.chmod(filename, stat.S_IWRITE)
            except:
                logger.warning('Cannot change permissions of ' + filename, logger.WARNING)

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
    host = nzbtomedia.CFG["WakeOnLan"]["host"]
    port = int(nzbtomedia.CFG["WakeOnLan"]["port"])
    mac = nzbtomedia.CFG["WakeOnLan"]["mac"]

    i = 1
    while TestCon(host, port) == "Down" and i < 4:
        logger.info(("Sending WakeOnLan Magic Packet for mac: %s" % (mac)))
        WakeOnLan(mac)
        time.sleep(20)
        i = i + 1

    if TestCon(host, port) == "Down":  # final check.
        logger.warning("System with mac: %s has not woken after 3 attempts. Continuing with the rest of the script." % (
        mac))
    else:
        logger.info("System with mac: %s has been woken. Continuing with the rest of the script." % (mac))


def convert_to_ascii(inputName, dirName):
    ascii_convert = int(nzbtomedia.CFG["ASCII"]["convert"])
    if ascii_convert == 0 or os.name == 'nt':  # just return if we don't want to convert or on windows os and "\" is replaced!.
        return inputName, dirName

    inputName2 = str(inputName.decode('ascii', 'replace').replace(u'\ufffd', '_'))
    dirName2 = str(dirName.decode('ascii', 'replace').replace(u'\ufffd', '_'))
    if dirName != dirName2:
        logger.info("Renaming directory:%s  to: %s." % (dirName, dirName2))
        shutil.move(dirName, dirName2)
    for dirpath, dirnames, filesnames in os.walk(dirName2):
        for filename in filesnames:
            filename2 = str(filename.decode('ascii', 'replace').replace(u'\ufffd', '_'))
            if filename != filename2:
                logger.info("Renaming file:%s  to: %s." % (filename, filename2))
                shutil.move(filename, filename2)
    inputName = inputName2
    dirName = dirName2
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
    except:
        return None, None, None, None, None


def getDirs(section, subsection):
    to_return = []

    def processDir(path):
        folders = []

        logger.info("Searching %s for mediafiles to post-process ..." % (path))

        # search for single files and move them into there own folder for post-processing
        for mediafile in listMediaFiles(path):
            parentDir = os.path.dirname(mediafile)
            if parentDir == path:
                newPath = None
                fileExt = os.path.splitext(os.path.basename(mediafile))[1]

                try:
                    if fileExt in nzbtomedia.AUDIOCONTAINER:
                        f = beets.mediafile.MediaFile(mediafile)

                        # get artist and album info
                        artist = f.artist
                        album = f.album

                        # create new path
                        newPath = os.path.join(parentDir, "%s - %s" % (sanitizeName(artist), sanitizeName(album)))
                    elif fileExt in nzbtomedia.MEDIACONTAINER:
                        f = guessit.guess_video_info(mediafile)

                        # get title
                        title = None
                        try:
                            title = f['series']
                        except:
                            title = f['title']

                        if not title:
                            title = os.path.basename(mediafile)

                        newPath = os.path.join(parentDir, sanitizeName(title))
                except Exception, e:
                    logger.info("Exception from MediaFile for: %s: %s" % (dir, e))

                # create new path if it does not exist
                if not os.path.exists(newPath):
                    makeDir(newPath)

                # move file to its new path
                shutil.move(mediafile, newPath)

        removeEmptyFolders(path, removeRoot=False)

        if os.listdir(path):
            folders.extend([os.path.join(path, o) for o in os.listdir(path) if
                            os.path.isdir(os.path.join(path, o))])
        return folders

    try:
        watch_dir = os.path.join(nzbtomedia.CFG[section][subsection]["watch_dir"], subsection)
        if os.path.exists(watch_dir):
            to_return.extend(processDir(watch_dir))
    except:pass

    try:
        outputDirectory = os.path.join(nzbtomedia.OUTPUTDIRECTORY, subsection)
        if os.path.exists(outputDirectory):
            to_return.extend(processDir(outputDirectory))
    except:pass

    if not to_return:
        logger.debug("No directories identified in %s:%s for post-processing" % (section,subsection))

    return list(set(to_return))

def rmDir(dirName):
    logger.info("Deleting %s" % (dirName))
    try:
        shutil.rmtree(dirName, True)
    except:
        logger.error("Unable to delete folder %s" % (dirName))

def cleanDir(path, section, subsection):
    if not os.path.exists(path):
        logger.info('Directory %s has been processed and removed ...' % (path), 'CLEANDIR')
        return

    try:
        minSize = int(nzbtomedia.CFG[section][subsection]['minSize'])
    except:minSize = 0
    try:
        delete_ignored = int(nzbtomedia.CFG[section][subsection]['delete_ignored'])
    except:delete_ignored = 0

    num_files = len(listMediaFiles(path, minSize=minSize, delete_ignored=delete_ignored))
    if num_files > 0:
        logger.info(
            "Directory %s still contains %s unprocessed file(s), skipping ..." % (path, num_files),
            'CLEANDIRS')

    logger.info("Directory %s has been processed, removing ..." % (path), 'CLEANDIRS')
    shutil.rmtree(path)

def create_torrent_class(clientAgent):
    # Hardlink solution for Torrents
    tc = None

    if clientAgent == 'utorrent':
        try:
            logger.debug("Connecting to %s: %s" % (clientAgent, nzbtomedia.UTORRENTWEBUI))
            tc = UTorrentClient(nzbtomedia.UTORRENTWEBUI, nzbtomedia.UTORRENTUSR, nzbtomedia.UTORRENTPWD)
        except:
            logger.error("Failed to connect to uTorrent")

    if clientAgent == 'transmission':
        try:
            logger.debug("Connecting to %s: http://%s:%s" % (
                clientAgent, nzbtomedia.TRANSMISSIONHOST, nzbtomedia.TRANSMISSIONPORT))
            tc = TransmissionClient(nzbtomedia.TRANSMISSIONHOST, nzbtomedia.TRANSMISSIONPORT,
                                              nzbtomedia.TRANSMISSIONUSR,
                                              nzbtomedia.TRANSMISSIONPWD)
        except:
            logger.error("Failed to connect to Transmission")

    if clientAgent == 'deluge':
        try:
            logger.debug("Connecting to %s: http://%s:%s" % (clientAgent, nzbtomedia.DELUGEHOST, nzbtomedia.DELUGEPORT))
            tc = DelugeClient()
            tc.connect(host=nzbtomedia.DELUGEHOST, port=nzbtomedia.DELUGEPORT, username=nzbtomedia.DELUGEUSR,
                                 password=nzbtomedia.DELUGEPWD)
        except:
            logger.error("Failed to connect to Deluge")

    return tc


def pause_torrent(clientAgent, inputHash, inputID, inputName):
    logger.debug("Stoping torrent %s in %s while processing" % (inputName, clientAgent))

    if clientAgent == 'utorrent' and nzbtomedia.TORRENT_CLASS != "":
        nzbtomedia.TORRENT_CLASS.stop(inputHash)
    if clientAgent == 'transmission' and nzbtomedia.TORRENT_CLASS != "":
        nzbtomedia.TORRENT_CLASS.stop_torrent(inputID)
    if clientAgent == 'deluge' and nzbtomedia.TORRENT_CLASS != "":
        nzbtomedia.TORRENT_CLASS.core.pause_torrent([inputID])

    time.sleep(5)


def resume_torrent(clientAgent, inputHash, inputID, inputName):
    logger.debug("Starting torrent %s in %s" % (inputName, clientAgent))

    if clientAgent == 'utorrent' and nzbtomedia.TORRENT_CLASS != "":
        nzbtomedia.TORRENT_CLASS.start(inputHash)
    if clientAgent == 'transmission' and nzbtomedia.TORRENT_CLASS != "":
        nzbtomedia.TORRENT_CLASS.start_torrent(inputID)
    if clientAgent == 'deluge' and nzbtomedia.TORRENT_CLASS != "":
        nzbtomedia.TORRENT_CLASS.core.resume_torrent([inputID])

    time.sleep(5)

def remove_torrent(clientAgent, inputHash, inputID, inputName):
    if nzbtomedia.DELETE_ORIGINAL == 1 or nzbtomedia.USELINK == 'move':
        logger.debug("Deleting torrent %s from %s" % (inputName, clientAgent))

        if clientAgent == 'utorrent' and nzbtomedia.TORRENT_CLASS != "":
            nzbtomedia.TORRENT_CLASS.removedata(inputHash)
            nzbtomedia.TORRENT_CLASS.remove(inputHash)
        if clientAgent == 'transmission' and nzbtomedia.TORRENT_CLASS != "":
            nzbtomedia.TORRENT_CLASS.remove_torrent(inputID, True)
        if clientAgent == 'deluge' and nzbtomedia.TORRENT_CLASS != "":
            nzbtomedia.TORRENT_CLASS.core.remove_torrent(inputID, True)

        time.sleep(5)

    else:
        resume_torrent(clientAgent, inputHash, inputID, inputName)

def find_download(clientAgent, download_id):
    logger.debug("Searching for Download on %s ..." % (clientAgent))
    if clientAgent == 'utorrent':
        torrents = nzbtomedia.TORRENT_CLASS.list()[1]['torrents']
        for torrent in torrents:
            if download_id in torrent:
                return True
    if clientAgent == 'transmission':
        torrents = nzbtomedia.TORRENT_CLASS.get_torrents()
        for torrent in torrents:
            hash = torrent.hashString
            if hash == download_id:
                return True
    if clientAgent == 'deluge':
        pass
    if clientAgent == 'sabnzbd':
        baseURL = "http://%s:%s/api" % (nzbtomedia.SABNZBDHOST, nzbtomedia.SABNZBDPORT)
        url = baseURL
        params = {}
        params['apikey'] = nzbtomedia.SABNZBDAPIKEY
        params['mode'] = "get_files"
        params['output'] = 'json'
        params['value'] = download_id
        try:
            r = requests.get(url, params=params, verify=False)
        except requests.ConnectionError:
            logger.error("Unable to open URL")
            return 1  # failure

        result = r.json()
        if result['files']:
            return True


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
    for regext in nzbtomedia.COMPRESSEDCONTAINER:
        if regext.search(filename):
            return regext.split(filename)[0]
    return False

def isMediaFile(mediafile, media=True, audio=True, meta=True, archives=True):
    fileName, fileExt = os.path.splitext(mediafile)

    # ignore MAC OS's retarded "resource fork" files
    if fileName.startswith('._'):
        return False

    if (media and fileExt.lower() in nzbtomedia.MEDIACONTAINER)\
        or (audio and fileExt.lower() in nzbtomedia.AUDIOCONTAINER)\
        or (meta and fileExt.lower() in nzbtomedia.METACONTAINER)\
        or (archives and is_archive_file(mediafile)):
        return True
    else:
        return False

def listMediaFiles(path, minSize=0, delete_ignored=0, media=True, audio=True, meta=True, archives=True):
    if not os.path.isdir(path):
        return []

    files = []
    for curFile in os.listdir(path):
        fullCurFile = os.path.join(path, curFile)

        # if it's a folder do it recursively
        if os.path.isdir(fullCurFile) and not curFile.startswith('.'):
            files += listMediaFiles(fullCurFile, minSize, delete_ignored, media, audio, meta, archives)

        elif isMediaFile(curFile, media, audio, meta, archives):
            # Optionally ignore sample files
            if is_sample(fullCurFile) or not is_minSize(fullCurFile, minSize):
                if delete_ignored == 1:
                    try:
                        os.unlink(fullCurFile)
                        logger.debug('Ignored file %s has been removed ...' % (curFile))
                    except:pass
                continue

            files.append(fullCurFile)

    return files

def find_imdbid(dirName, inputName):
    imdbid = None

    logger.info('Attemping imdbID lookup for %s' % (inputName))

    # find imdbid in dirName
    logger.info('Searching folder and file names for imdbID ...')
    m = re.search('(tt\d{7})', dirName+inputName)
    if m:
        imdbid = m.group(1)
        logger.info("Found imdbID [%s]" % imdbid)
        return imdbid

    logger.info('Searching IMDB for imdbID ...')
    guess = guessit.guess_movie_info(inputName)
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

        logger.debug("Opening URL: %s" % url)

        try:
            r = requests.get(url, params={'y': year, 't': title}, verify=False)
        except requests.ConnectionError:
            logger.error("Unable to open URL %s" % url)
            return

        results = r.json()

        try:
            imdbid = results['imdbID']
        except:
            pass

        if imdbid:
            logger.info("Found imdbID [%s]" % imdbid)
            return imdbid

    logger.warning('Unable to find a imdbID for %s' % (inputName))

def extractFiles(src, dst=None):
    extracted_folder = []

    for inputFile in listMediaFiles(src, media=False, audio=False, meta=False, archives=True):
        dirPath = os.path.dirname(inputFile)
        fullFileName = os.path.basename(inputFile)

        if dirPath in extracted_folder:
            break

        try:
            if extractor.extract(inputFile, dirPath or dst):
                extracted_folder.append(dirPath or dst)
        except Exception, e:
            logger.error("Extraction failed for: %s" % (fullFileName))

    if extracted_folder:
        for folder in extracted_folder:
            for inputFile in listMediaFiles(folder):
                fullFileName = os.path.basename(inputFile)

                if is_archive_file(inputFile):
                    logger.info("Removing extracted archive %s from folder %s ..." % (fullFileName, folder))
                    try:
                        os.remove(inputFile)
                        time.sleep(1)
                    except:
                        logger.debug("Unable to remove file %s" % (inputFile))

def backupVersionedFile(old_file, version):
    numTries = 0

    new_file = old_file + '.' + 'v' + str(version)

    while not os.path.isfile(new_file):
        if not os.path.isfile(old_file):
            logger.log(u"Not creating backup, " + old_file + " doesn't exist", logger.DEBUG)
            break

        try:
            logger.log(u"Trying to back up " + old_file + " to " + new_file, logger.DEBUG)
            shutil.copy(old_file, new_file)
            logger.log(u"Backup done", logger.DEBUG)
            break
        except Exception, e:
            logger.log(u"Error while trying to back up " + old_file + " to " + new_file + " : " + str(e), logger.WARNING)
            numTries += 1
            time.sleep(1)
            logger.log(u"Trying again.", logger.DEBUG)

        if numTries >= 10:
            logger.log(u"Unable to back up " + old_file + " to " + new_file + " please do it manually.", logger.ERROR)
            return False

    return True


def update_downloadInfoStatus(inputName, status):
    logger.db("Updating status of our download %s in the DB to %s" % (inputName, status))

    myDB = nzbToMediaDB.DBConnection()
    myDB.action("UPDATE downloads SET status=?, last_update=? WHERE input_name=?",
                [status, datetime.date.today().toordinal(), inputName])


def get_downloadInfo(inputName, status):
    logger.db("Getting download info for %s from the DB" % (inputName))

    myDB = nzbToMediaDB.DBConnection()
    sqlResults = myDB.select("SELECT * FROM downloads WHERE input_name=? AND status=?",
                             [inputName, status])

    return sqlResults