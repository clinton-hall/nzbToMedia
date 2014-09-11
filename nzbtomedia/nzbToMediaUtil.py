from __future__ import unicode_literals
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
import nzbtomedia
from babelfish import Language
import subliminal 

from nzbtomedia.extractor import extractor
from nzbtomedia.linktastic import linktastic
from nzbtomedia.synchronousdeluge.client import DelugeClient
from nzbtomedia.utorrent.client import UTorrentClient
from nzbtomedia.transmissionrpc.client import Client as TransmissionClient
from nzbtomedia import logger, nzbToMediaDB

def reportNzb(failure_link, clientAgent):
    # Contact indexer site
    logger.info("Sending failure notification to indexer site")
    if clientAgent == 'nzbget':
        headers = {'User-Agent' : 'NZBGet / nzbToMedia.py'}
    elif clientAgent == 'sabnzbd':
        headers = {'User-Agent' : 'SABnzbd / nzbToMedia.py'}
    else:
        return
    try:
        r = requests.post(failure_link, headers=headers)
    except requests.ConnectionError:
        logger.error("Unable to open URL %s" % failure_link)
    return

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
    name = re.sub(r'[\\\/*]', '-', name)
    name = re.sub(r'[:"<>|?]', '', name)

    # remove leading/trailing periods and spaces
    name = name.strip(' .')
    try:
        name = name.encode(nzbtomedia.SYS_ENCODING)
    except: pass

    return name
     
def makeDir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except Exception, e:
            return False
    return True

def remoteDir(path):
    for local,remote in nzbtomedia.REMOTEPATHS:
        if local in path:
            base_dirs = path.replace(local,"").split(os.sep)
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
        inputName = inputName.encode(nzbtomedia.SYS_ENCODING)
    except: pass
    try:
        inputDirectory = inputDirectory.encode(nzbtomedia.SYS_ENCODING)
    except: pass

    if inputDirectory is None:  # =Nothing to process here.
        return inputDirectory, inputName, inputCategory, root

    pathlist = os.path.normpath(inputDirectory).split(os.sep)

    if inputCategory and inputCategory in pathlist: 
        logger.debug("SEARCH: Found the Category: %s in directory structure" % (inputCategory))
    elif inputCategory:
        logger.debug("SEARCH: Could not find the category: %s in the directory structure" % (inputCategory))
    else:
        try:
            inputCategory = list(set(pathlist) & set(categories))[-1]  # assume last match is most relevant category.
            logger.debug("SEARCH: Found Category: %s in directory structure" % (inputCategory))
        except IndexError:
            inputCategory = ""
            logger.debug("SEARCH: Could not find a category in the directory structure")
    if not os.path.isdir(inputDirectory) and os.path.isfile(inputDirectory):  # If the input directory is a file
        if not inputName: inputName = os.path.split(os.path.normpath(inputDirectory))[1]
        return inputDirectory, inputName, inputCategory, root

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
    elif inputName and os.path.isdir(os.path.join(inputDirectory, sanitizeName(inputName))):
        logger.info("SEARCH: Found torrent directory %s in input directory directory %s" % (
            sanitizeName(inputName), inputDirectory))
        inputDirectory = os.path.join(inputDirectory, sanitizeName(inputName))
        logger.info("SEARCH: Setting inputDirectory to %s" % (inputDirectory))
        tordir = True
    elif inputName and os.path.isfile(os.path.join(inputDirectory, inputName)):
        logger.info("SEARCH: Found torrent file %s in input directory directory %s" % (inputName, inputDirectory))
        inputDirectory = os.path.join(inputDirectory, inputName)
        logger.info("SEARCH: Setting inputDirectory to %s" % (inputDirectory))
        tordir = True
    elif inputName and os.path.isfile(os.path.join(inputDirectory, sanitizeName(inputName))):
        logger.info("SEARCH: Found torrent file %s in input directory directory %s" % (
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

    return inputDirectory, inputName, inputCategory, root

def getDirSize(inputPath):
   from functools import partial
   prepend = partial(os.path.join, inputPath)
   return sum([(os.path.getsize(f) if os.path.isfile(f) else getDirSize(f)) for f in map(prepend, os.listdir(inputPath))])

def is_minSize(inputName, minSize):
    fileName, fileExt = os.path.splitext(os.path.basename(inputName))


    # audio files we need to check directory size not file size
    inputSize = os.path.getsize(inputName)
    if fileExt in (nzbtomedia.AUDIOCONTAINER):
        try:
            inputSize = getDirSize(os.path.dirname(inputName))
        except:
            logger.error("Failed to get file size for %s" % (inputName), 'MINSIZE')
            return True

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
        return encoded, Name.encode(nzbtomedia.SYS_ENCODING)
    for Idx in range(len(Name)):
        # /!\ detection is done 2char by 2char for UTF-8 special character
        if (len(Name) != 1) & (Idx < (len(Name) - 1)):
            # Detect UTF-8
            if ((Name[Idx] == '\xC2') | (Name[Idx] == '\xC3')) & ((Name[Idx+1] >= '\xA0') & (Name[Idx+1] <= '\xFF')):
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
    if encoding and not encoding == nzbtomedia.SYS_ENCODING:
        encoded = True
        Name = Name.decode(encoding).encode(nzbtomedia.SYS_ENCODING)
    return encoded, Name


def convert_to_ascii(inputName, dirName):
    ascii_convert = int(nzbtomedia.CFG["ASCII"]["convert"])
    if ascii_convert == 0 or os.name == 'nt':  # just return if we don't want to convert or on windows os and "\" is replaced!.
        return inputName, dirName

    encoded, inputName = CharReplace(inputName)

    dir, base = os.path.split(dirName)
    if not base:  # ended with "/"
        dir, base = os.path.split(dir)

    encoded, base2 = CharReplace(base)
    if encoded:
        dirName = os.path.join(dir, base2)
        logger.info("Renaming directory to: %s." % (base2), 'ENCODER')
        os.rename(os.path.join(dir,base), dirName)
        if os.environ.has_key('NZBOP_SCRIPTDIR'):
            print "[NZB] DIRECTORY=%s" % (dirName)  # Return the new directory to NZBGet.

    for dirname, dirnames, filenames in os.walk(dirName, topdown=False):
        for subdirname in dirnames:
            encoded, subdirname2 = CharReplace(subdirname)
            if encoded:
                logger.info("Renaming directory to: %s." % (subdirname2), 'ENCODER')
                os.rename(os.path.join(dirname, subdirname), os.path.join(dirname, subdirname2))

    for dirname, dirnames, filenames in os.walk(dirName):
        for filename in filenames:
            encoded, filename2 = CharReplace(filename)
            if encoded:
                logger.info("Renaming file to: %s." % (filename2), 'ENCODER')
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


def getDirs(section, subsection, link = 'hard'):
    to_return = []

    def processDir(path):
        folders = []

        logger.info("Searching %s for mediafiles to post-process ..." % (path))
        sync = [ o for o in os.listdir(path) if os.path.splitext(o)[1] == '.!sync' ]
        # search for single files and move them into their own folder for post-processing
        for mediafile in [ os.path.join(path, o) for o in os.listdir(path) if
                            os.path.isfile(os.path.join(path, o)) ]:
            if len(sync) > 0:
                break
            try:
                logger.debug("Found file %s in root directory %s." % (os.path.split(mediafile)[1], path)) 
                newPath = None
                fileExt = os.path.splitext(mediafile)[1]
                try:
                    if fileExt in nzbtomedia.AUDIOCONTAINER:
                        f = beets.mediafile.MediaFile(mediafile)

                        # get artist and album info
                        artist = f.artist
                        album = f.album

                        # create new path
                        newPath = os.path.join(path, "%s - %s" % (sanitizeName(artist), sanitizeName(album)))
                    elif fileExt in nzbtomedia.MEDIACONTAINER:
                        f = guessit.guess_video_info(mediafile)

                        # get title
                        title = None
                        try:
                            title = f['series']
                        except:
                            title = f['title']

                        if not title:
                            title = os.path.splitext(os.path.basename(mediafile))[0]

                        newPath = os.path.join(path, sanitizeName(title))
                except Exception as e:
                    logger.error("Exception parsing name for media file: %s: %s" % (os.path.split(mediafile)[1], e))

                if not newPath:
                    title = os.path.splitext(os.path.basename(mediafile))[0]
                    newPath = os.path.join(path, sanitizeName(title))

                try:
                   newPath = newPath.encode(nzbtomedia.SYS_ENCODING)
                except: pass

                # Just fail-safe incase we already have afile with this clean-name (was actually a bug from earlier code, but let's be safe).
                if os.path.isfile(newPath):
                    newPath2 = os.path.join(os.path.join(os.path.split(newPath)[0], 'new'), os.path.split(newPath)[1])
                    newPath = newPath2

                # create new path if it does not exist
                if not os.path.exists(newPath):
                    makeDir(newPath)

                newfile = os.path.join(newPath, sanitizeName(os.path.split(mediafile)[1]))
                try:
                    newfile = newfile.encode(nzbtomedia.SYS_ENCODING)
                except: pass

                # link file to its new path
                copy_link(mediafile, newfile, link)
            except Exception as e:
                logger.error("Failed to move %s to its own directory: %s" % (os.path.split(mediafile)[1], e))

        #removeEmptyFolders(path, removeRoot=False)

        if os.listdir(path):
            for dir in [os.path.join(path, o) for o in os.listdir(path) if
                            os.path.isdir(os.path.join(path, o))]:
                sync = [ o for o in os.listdir(dir) if os.path.splitext(o)[1] == '.!sync' ]
                if len(sync) > 0 or len(os.listdir(dir)) == 0:
                    continue
                folders.extend([dir])
        return folders

    try:
        watch_dir = os.path.join(nzbtomedia.CFG[section][subsection]["watch_dir"], subsection)
        if os.path.exists(watch_dir):
            to_return.extend(processDir(watch_dir))
        elif os.path.exists(nzbtomedia.CFG[section][subsection]["watch_dir"]):
            to_return.extend(processDir(nzbtomedia.CFG[section][subsection]["watch_dir"]))
    except Exception as e:
        logger.error("Failed to add directories from %s for post-processing: %s" % (nzbtomedia.CFG[section][subsection]["watch_dir"], e))

    if nzbtomedia.USELINK == 'move':
        try:
            outputDirectory = os.path.join(nzbtomedia.OUTPUTDIRECTORY, subsection)
            if os.path.exists(outputDirectory):
                to_return.extend(processDir(outputDirectory))
        except Exception as e:
            logger.error("Failed to add directories from %s for post-processing: %s" % (nzbtomedia.OUTPUTDIRECTORY, e))

    if not to_return:
        logger.debug("No directories identified in %s:%s for post-processing" % (section,subsection))

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
        raise

def rmDir(dirName):
    logger.info("Deleting %s" % (dirName))
    try:
        shutil.rmtree(dirName, onerror=onerror)
    except:
        logger.error("Unable to delete folder %s" % (dirName))

def cleanDir(path, section, subsection):
    if not os.path.exists(path):
        logger.info('Directory %s has been processed and removed ...' % (path), 'CLEANDIR')
        return
    if nzbtomedia.FORCE_CLEAN:
        logger.info('Doing Forceful Clean of %s' % (path), 'CLEANDIR')
        rmDir(path)
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
        return

    logger.info("Directory %s has been processed, removing ..." % (path), 'CLEANDIRS')
    try:
        shutil.rmtree(path, onerror=onerror)
    except:
        logger.error("Unable to delete directory %s" % (path))

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
    logger.debug("Stopping torrent %s in %s while processing" % (inputName, clientAgent))

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
        return False
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
            return False  # failure

        result = r.json()
        if result['files']:
            return True
    return False


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
    files = []
    if not os.path.isdir(path): 
        if os.path.isfile(path):  # Single file downloads.
            curFile = os.path.split(path)[1]
            if isMediaFile(curFile, media, audio, meta, archives):
                # Optionally ignore sample files
                if is_sample(path) or not is_minSize(path, minSize):
                    if delete_ignored == 1:
                        try:
                            os.unlink(path)
                            logger.debug('Ignored file %s has been removed ...' % (curFile))
                        except:pass
                else:
                    files.append(path)

        return files

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
    for file in os.listdir(dirName):
        m = re.search('(tt\d{7})', file)
        if m:
            imdbid = m.group(1)
            logger.info("Found imdbID [%s] via file name" % imdbid)
            return imdbid
    if os.environ.has_key('NZBPR__DNZB_MOREINFO'):
        dnzb_more_info=os.environ.get('NZBPR__DNZB_MOREINFO', '')
        if dnzb_more_info != '':
            regex = re.compile(r'^http://www.imdb.com/title/(tt[0-9]+)/$', re.IGNORECASE)
            m = regex.match(dnzb_more_info)
            if m:
                imdbid = m.group(1)
                logger.info("Found imdbID [%s] from DNZB-MoreInfo" % imdbid)
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
    extracted_archive = []

    for inputFile in listMediaFiles(src, media=False, audio=False, meta=False, archives=True):
        dirPath = os.path.dirname(inputFile)
        fullFileName = os.path.basename(inputFile)
        archiveName = os.path.splitext(fullFileName)[0]
        archiveName = re.sub(r"part[0-9]+", "", archiveName)

        if dirPath in extracted_folder and archiveName in extracted_archive:
            continue  # no need to extract this, but keep going to look for other archives and sub directories.

        try:
            if extractor.extract(inputFile, dirPath or dst):
                extracted_folder.append(dirPath or dst)
                extracted_archive.append(archiveName)
        except Exception, e:
            logger.error("Extraction failed for: %s" % (fullFileName))

    for folder in extracted_folder:
        for inputFile in listMediaFiles(folder, media=False, audio=False, meta=False, archives=True):
            fullFileName = os.path.basename(inputFile)
            archiveName = os.path.splitext(fullFileName)[0]
            archiveName = re.sub(r"part[0-9]+", "", archiveName)
            if not archiveName in extracted_archive:
                continue  # don't remove if we haven't extracted this archive.
            logger.info("Removing extracted archive %s from folder %s ..." % (fullFileName, folder))
            try:
                os.remove(inputFile)
                time.sleep(1)
            except:
                logger.debug("Unable to remove file %s" % (inputFile))

def import_subs(filename):
    if not nzbtomedia.GETSUBS:
        return
    try:
        subliminal.cache_region.configure('dogpile.cache.memory')
    except:
        pass   

    languages = set()
    for item in nzbtomedia.SLANGUAGES:
        try:
            languages.add(Language(item))
        except:
            pass
    if not languages:
        return

    logger.debug("Attempting to download subtitles for %s" %(filename), 'SUBTITLES')
    try:
        video = subliminal.scan_video(filename, subtitles=True, embedded_subtitles=True)
        subtitles = subliminal.download_best_subtitles([video], languages, hearing_impaired=False)
        subliminal.save_subtitles(subtitles)
    except:
        logger.error("Failed to download subtitles for %s" %(filename), 'SUBTITLES') 

def server_responding(baseURL):
    try:
        requests.get(baseURL, timeout=60, verify=False)
        return True
    except (requests.ConnectionError, requests.exceptions.Timeout):
        return False

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
                [status, datetime.date.today().toordinal(), unicode(inputName)])


def get_downloadInfo(inputName, status):
    logger.db("Getting download info for %s from the DB" % (inputName))

    myDB = nzbToMediaDB.DBConnection()
    sqlResults = myDB.select("SELECT * FROM downloads WHERE input_name=? AND status=?",
                             [unicode(inputName), status])

    return sqlResults

class RunningProcess():
    """ Limits application to single instance """

    def __init__(self):
        if platform.system() == 'Windows':
            self.process = WindowsProcess()
        else:
            self.process = PosixProcess()

    def alreadyrunning(self):
        return self.process.alreadyrunning()

    #def __del__(self):
    #    self.process.__del__()

class WindowsProcess():

    def __init__(self):
        self.mutexname = "nzbtomedia_{D0E858DF-985E-4907-B7FB-8D732C3FC3B9}"
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
        if (self.lasterror == self.ERROR_ALREADY_EXISTS):
            self.CloseHandle(self.mutex)
            return True
        else:
            return False
            

    def __del__(self):
        if self.mutex:
            self.CloseHandle(self.mutex)

class PosixProcess():

    def __init__(self):
        self.pidpath = nzbtomedia.PID_FILE

    def alreadyrunning(self):
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
            except: pass

        return self.lasterror

    def __del__(self):
        if not self.lasterror:
            if os.path.isfile(self.pidpath):
                os.unlink(self.pidpath)
