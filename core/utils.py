# coding=utf-8

from __future__ import print_function, unicode_literals

import datetime
from functools import partial
import os
import re
import shutil
import socket
import stat
import struct
import time

from babelfish import Language
import beets
import guessit
import linktastic
from qbittorrent import Client as qBittorrentClient
import requests
from six import text_type
import subliminal
from synchronousdeluge.client import DelugeClient
from transmissionrpc.client import Client as TransmissionClient
from utorrent.client import UTorrentClient

import core
from core import extractor, logger, main_db

try:
    from win32event import CreateMutex
    from win32api import CloseHandle, GetLastError
    from winerror import ERROR_ALREADY_EXISTS
except ImportError:
    if os.name == 'nt':
        raise

try:
    import jaraco
except ImportError:
    if os.name == 'nt':
        raise

requests.packages.urllib3.disable_warnings()

# Monkey Patch shutil.copyfileobj() to adjust the buffer length to 512KB rather than 4KB
shutil.copyfileobjOrig = shutil.copyfileobj


def copyfileobj_fast(fsrc, fdst, length=512 * 1024):
    shutil.copyfileobjOrig(fsrc, fdst, length=length)


shutil.copyfileobj = copyfileobj_fast


def report_nzb(failure_link, client_agent):
    # Contact indexer site
    logger.info("Sending failure notification to indexer site")
    if client_agent == 'nzbget':
        headers = {'User-Agent': 'NZBGet / nzbToMedia.py'}
    elif client_agent == 'sabnzbd':
        headers = {'User-Agent': 'SABnzbd / nzbToMedia.py'}
    else:
        return
    try:
        requests.post(failure_link, headers=headers, timeout=(30, 300))
    except Exception as e:
        logger.error("Unable to open URL {0} due to {1}".format(failure_link, e))
    return


def sanitize_name(name):
    """
    >>> sanitize_name('a/b/c')
    'a-b-c'
    >>> sanitize_name('abc')
    'abc'
    >>> sanitize_name('a"b')
    'ab'
    >>> sanitize_name('.a.b..')
    'a.b'
    """

    # remove bad chars from the filename
    name = re.sub(r'[\\\/*]', '-', name)
    name = re.sub(r'[:"<>|?]', '', name)

    # remove leading/trailing periods and spaces
    name = name.strip(' .')
    try:
        name = name.encode(core.SYS_ENCODING)
    except Exception:
        pass

    return name


def make_dir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except Exception:
            return False
    return True


def remote_dir(path):
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


def category_search(input_directory, input_name, input_category, root, categories):
    tordir = False

    try:
        input_name = input_name.encode(core.SYS_ENCODING)
    except Exception:
        pass
    try:
        input_directory = input_directory.encode(core.SYS_ENCODING)
    except Exception:
        pass

    if input_directory is None:  # =Nothing to process here.
        return input_directory, input_name, input_category, root

    pathlist = os.path.normpath(input_directory).split(os.sep)

    if input_category and input_category in pathlist:
        logger.debug("SEARCH: Found the Category: {0} in directory structure".format(input_category))
    elif input_category:
        logger.debug("SEARCH: Could not find the category: {0} in the directory structure".format(input_category))
    else:
        try:
            input_category = list(set(pathlist) & set(categories))[-1]  # assume last match is most relevant category.
            logger.debug("SEARCH: Found Category: {0} in directory structure".format(input_category))
        except IndexError:
            input_category = ""
            logger.debug("SEARCH: Could not find a category in the directory structure")
    if not os.path.isdir(input_directory) and os.path.isfile(input_directory):  # If the input directory is a file
        if not input_name:
            input_name = os.path.split(os.path.normpath(input_directory))[1]
        return input_directory, input_name, input_category, root

    if input_category and os.path.isdir(os.path.join(input_directory, input_category)):
        logger.info(
            "SEARCH: Found category directory {0} in input directory directory {1}".format(input_category, input_directory))
        input_directory = os.path.join(input_directory, input_category)
        logger.info("SEARCH: Setting input_directory to {0}".format(input_directory))
    if input_name and os.path.isdir(os.path.join(input_directory, input_name)):
        logger.info("SEARCH: Found torrent directory {0} in input directory directory {1}".format(input_name, input_directory))
        input_directory = os.path.join(input_directory, input_name)
        logger.info("SEARCH: Setting input_directory to {0}".format(input_directory))
        tordir = True
    elif input_name and os.path.isdir(os.path.join(input_directory, sanitize_name(input_name))):
        logger.info("SEARCH: Found torrent directory {0} in input directory directory {1}".format(
            sanitize_name(input_name), input_directory))
        input_directory = os.path.join(input_directory, sanitize_name(input_name))
        logger.info("SEARCH: Setting input_directory to {0}".format(input_directory))
        tordir = True
    elif input_name and os.path.isfile(os.path.join(input_directory, input_name)):
        logger.info("SEARCH: Found torrent file {0} in input directory directory {1}".format(input_name, input_directory))
        input_directory = os.path.join(input_directory, input_name)
        logger.info("SEARCH: Setting input_directory to {0}".format(input_directory))
        tordir = True
    elif input_name and os.path.isfile(os.path.join(input_directory, sanitize_name(input_name))):
        logger.info("SEARCH: Found torrent file {0} in input directory directory {1}".format(
            sanitize_name(input_name), input_directory))
        input_directory = os.path.join(input_directory, sanitize_name(input_name))
        logger.info("SEARCH: Setting input_directory to {0}".format(input_directory))
        tordir = True

    imdbid = [item for item in pathlist if '.cp(tt' in item]  # This looks for the .cp(tt imdb id in the path.
    if imdbid and '.cp(tt' not in input_name:
        input_name = imdbid[0]  # This ensures the imdb id is preserved and passed to CP
        tordir = True

    if input_category and not tordir:
        try:
            index = pathlist.index(input_category)
            if index + 1 < len(pathlist):
                tordir = True
                logger.info("SEARCH: Found a unique directory {0} in the category directory".format
                            (pathlist[index + 1]))
                if not input_name:
                    input_name = pathlist[index + 1]
        except ValueError:
            pass

    if input_name and not tordir:
        if input_name in pathlist or sanitize_name(input_name) in pathlist:
            logger.info("SEARCH: Found torrent directory {0} in the directory structure".format(input_name))
            tordir = True
        else:
            root = 1
    if not tordir:
        root = 2

    if root > 0:
        logger.info("SEARCH: Could not find a unique directory for this download. Assume a common directory.")
        logger.info("SEARCH: We will try and determine which files to process, individually")

    return input_directory, input_name, input_category, root


def get_dir_size(input_path):
    prepend = partial(os.path.join, input_path)
    return sum([
        (os.path.getsize(f) if os.path.isfile(f) else get_dir_size(f))
        for f in map(prepend, os.listdir(text_type(input_path)))
    ])


def is_min_size(input_name, min_size):
    file_name, file_ext = os.path.splitext(os.path.basename(input_name))

    # audio files we need to check directory size not file size
    input_size = os.path.getsize(input_name)
    if file_ext in core.AUDIOCONTAINER:
        try:
            input_size = get_dir_size(os.path.dirname(input_name))
        except Exception:
            logger.error("Failed to get file size for {0}".format(input_name), 'MINSIZE')
            return True

    # Ignore files under a certain size
    if input_size > min_size * 1048576:
        return True


def is_sample(input_name):
    # Ignore 'sample' in files
    if re.search('(^|[\W_])sample\d*[\W_]', input_name.lower()):
        return True


def copy_link(src, target_link, use_link):
    logger.info("MEDIAFILE: [{0}]".format(os.path.basename(target_link)), 'COPYLINK')
    logger.info("SOURCE FOLDER: [{0}]".format(os.path.dirname(src)), 'COPYLINK')
    logger.info("TARGET FOLDER: [{0}]".format(os.path.dirname(target_link)), 'COPYLINK')

    if src != target_link and os.path.exists(target_link):
        logger.info("MEDIAFILE already exists in the TARGET folder, skipping ...", 'COPYLINK')
        return True
    elif src == target_link and os.path.isfile(target_link) and os.path.isfile(src):
        logger.info("SOURCE AND TARGET files are the same, skipping ...", 'COPYLINK')
        return True
    elif src == os.path.dirname(target_link):
        logger.info("SOURCE AND TARGET folders are the same, skipping ...", 'COPYLINK')
        return True

    make_dir(os.path.dirname(target_link))
    try:
        if use_link == 'dir':
            logger.info("Directory linking SOURCE FOLDER -> TARGET FOLDER", 'COPYLINK')
            linktastic.dirlink(src, target_link)
            return True
        if use_link == 'junction':
            logger.info("Directory junction linking SOURCE FOLDER -> TARGET FOLDER", 'COPYLINK')
            linktastic.dirlink(src, target_link)
            return True
        elif use_link == "hard":
            logger.info("Hard linking SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
            linktastic.link(src, target_link)
            return True
        elif use_link == "sym":
            logger.info("Sym linking SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
            linktastic.symlink(src, target_link)
            return True
        elif use_link == "move-sym":
            logger.info("Sym linking SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
            shutil.move(src, target_link)
            linktastic.symlink(target_link, src)
            return True
        elif use_link == "move":
            logger.info("Moving SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
            shutil.move(src, target_link)
            return True
    except Exception as e:
        logger.warning("Error: {0}, copying instead ... ".format(e), 'COPYLINK')

    logger.info("Copying SOURCE MEDIAFILE -> TARGET FOLDER", 'COPYLINK')
    shutil.copy(src, target_link)

    return True


def replace_links(link):
    n = 0
    target = link
    if os.name == 'nt':
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


def flatten(output_destination):
    logger.info("FLATTEN: Flattening directory: {0}".format(output_destination))
    for outputFile in list_media_files(output_destination):
        dir_path = os.path.dirname(outputFile)
        file_name = os.path.basename(outputFile)

        if dir_path == output_destination:
            continue

        target = os.path.join(output_destination, file_name)

        try:
            shutil.move(outputFile, target)
        except Exception:
            logger.error("Could not flatten {0}".format(outputFile), 'FLATTEN')

    remove_empty_folders(output_destination)  # Cleanup empty directories


def remove_empty_folders(path, remove_root=True):
    """Function to remove empty folders"""
    if not os.path.isdir(path):
        return

    # remove empty subfolders
    logger.debug("Checking for empty folders in:{0}".format(path))
    files = os.listdir(text_type(path))
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                remove_empty_folders(fullpath)

    # if folder empty, delete it
    files = os.listdir(text_type(path))
    if len(files) == 0 and remove_root:
        logger.debug("Removing empty folder:{}".format(path))
        os.rmdir(path)


def remove_read_only(filename):
    if os.path.isfile(filename):
        # check first the read-only attribute
        file_attribute = os.stat(filename)[0]
        if not file_attribute & stat.S_IWRITE:
            # File is read-only, so make it writeable
            logger.debug('Read only mode on file {name}. Attempting to make it writeable'.format
                         (name=filename))
            try:
                os.chmod(filename, stat.S_IWRITE)
            except Exception:
                logger.warning('Cannot change permissions of {file}'.format(file=filename), logger.WARNING)


# Wake function
def wake_on_lan(ethernet_address):
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
def test_connection(host, port):
    try:
        socket.create_connection((host, port))
        return "Up"
    except Exception:
        return "Down"


def wake_up():
    host = core.CFG["WakeOnLan"]["host"]
    port = int(core.CFG["WakeOnLan"]["port"])
    mac = core.CFG["WakeOnLan"]["mac"]

    i = 1
    while test_connection(host, port) == "Down" and i < 4:
        logger.info(("Sending WakeOnLan Magic Packet for mac: {0}".format(mac)))
        wake_on_lan(mac)
        time.sleep(20)
        i = i + 1

    if test_connection(host, port) == "Down":  # final check.
        logger.warning("System with mac: {0} has not woken after 3 attempts. "
                       "Continuing with the rest of the script.".format(mac))
    else:
        logger.info("System with mac: {0} has been woken. Continuing with the rest of the script.".format(mac))


def char_replace(name):
    # Special character hex range:
    # CP850: 0x80-0xA5 (fortunately not used in ISO-8859-15)
    # UTF-8: 1st hex code 0xC2-0xC3 followed by a 2nd hex code 0xA1-0xFF
    # ISO-8859-15: 0xA6-0xFF
    # The function will detect if Name contains a special character
    # If there is special character, detects if it is a UTF-8, CP850 or ISO-8859-15 encoding
    encoded = False
    encoding = None
    if isinstance(name, text_type):
        return encoded, name.encode(core.SYS_ENCODING)
    for Idx in range(len(name)):
        # /!\ detection is done 2char by 2char for UTF-8 special character
        if (len(name) != 1) & (Idx < (len(name) - 1)):
            # Detect UTF-8
            if ((name[Idx] == '\xC2') | (name[Idx] == '\xC3')) & (
                    (name[Idx + 1] >= '\xA0') & (name[Idx + 1] <= '\xFF')):
                encoding = 'utf-8'
                break
            # Detect CP850
            elif (name[Idx] >= '\x80') & (name[Idx] <= '\xA5'):
                encoding = 'cp850'
                break
            # Detect ISO-8859-15
            elif (name[Idx] >= '\xA6') & (name[Idx] <= '\xFF'):
                encoding = 'iso-8859-15'
                break
        else:
            # Detect CP850
            if (name[Idx] >= '\x80') & (name[Idx] <= '\xA5'):
                encoding = 'cp850'
                break
            # Detect ISO-8859-15
            elif (name[Idx] >= '\xA6') & (name[Idx] <= '\xFF'):
                encoding = 'iso-8859-15'
                break
    if encoding and not encoding == core.SYS_ENCODING:
        encoded = True
        name = name.decode(encoding).encode(core.SYS_ENCODING)
    return encoded, name


def convert_to_ascii(input_name, dir_name):

    ascii_convert = int(core.CFG["ASCII"]["convert"])
    if ascii_convert == 0 or os.name == 'nt':  # just return if we don't want to convert or on windows os and "\" is replaced!.
        return input_name, dir_name

    encoded, input_name = char_replace(input_name)

    dir, base = os.path.split(dir_name)
    if not base:  # ended with "/"
        dir, base = os.path.split(dir)

    encoded, base2 = char_replace(base)
    if encoded:
        dir_name = os.path.join(dir, base2)
        logger.info("Renaming directory to: {0}.".format(base2), 'ENCODER')
        os.rename(os.path.join(dir, base), dir_name)
        if 'NZBOP_SCRIPTDIR' in os.environ:
            print("[NZB] DIRECTORY={0}".format(dir_name))

    for dirname, dirnames, filenames in os.walk(dir_name, topdown=False):
        for subdirname in dirnames:
            encoded, subdirname2 = char_replace(subdirname)
            if encoded:
                logger.info("Renaming directory to: {0}.".format(subdirname2), 'ENCODER')
                os.rename(os.path.join(dirname, subdirname), os.path.join(dirname, subdirname2))

    for dirname, dirnames, filenames in os.walk(dir_name):
        for filename in filenames:
            encoded, filename2 = char_replace(filename)
            if encoded:
                logger.info("Renaming file to: {0}.".format(filename2), 'ENCODER')
                os.rename(os.path.join(dirname, filename), os.path.join(dirname, filename2))

    return input_name, dir_name


def parse_other(args):
    return os.path.normpath(args[1]), '', '', '', ''


def parse_rtorrent(args):
    # rtorrent usage: system.method.set_key = event.download.finished,TorrentToMedia,
    # "execute={/path/to/nzbToMedia/TorrentToMedia.py,\"$d.get_base_path=\",\"$d.get_name=\",\"$d.get_custom1=\",\"$d.get_hash=\"}"
    input_directory = os.path.normpath(args[1])
    try:
        input_name = args[2]
    except Exception:
        input_name = ''
    try:
        input_category = args[3]
    except Exception:
        input_category = ''
    try:
        input_hash = args[4]
    except Exception:
        input_hash = ''
    try:
        input_id = args[4]
    except Exception:
        input_id = ''

    return input_directory, input_name, input_category, input_hash, input_id


def parse_utorrent(args):
    # uTorrent usage: call TorrentToMedia.py "%D" "%N" "%L" "%I"
    input_directory = os.path.normpath(args[1])
    input_name = args[2]
    try:
        input_category = args[3]
    except Exception:
        input_category = ''
    try:
        input_hash = args[4]
    except Exception:
        input_hash = ''
    try:
        input_id = args[4]
    except Exception:
        input_id = ''

    return input_directory, input_name, input_category, input_hash, input_id


def parse_deluge(args):
    # Deluge usage: call TorrentToMedia.py TORRENT_ID TORRENT_NAME TORRENT_DIR
    input_directory = os.path.normpath(args[3])
    input_name = args[2]
    input_hash = args[1]
    input_id = args[1]
    try:
        input_category = core.TORRENT_CLASS.core.get_torrent_status(input_id, ['label']).get()['label']
    except Exception:
        input_category = ''
    return input_directory, input_name, input_category, input_hash, input_id


def parse_transmission(args):
    # Transmission usage: call TorrenToMedia.py (%TR_TORRENT_DIR% %TR_TORRENT_NAME% is passed on as environmental variables)
    input_directory = os.path.normpath(os.getenv('TR_TORRENT_DIR'))
    input_name = os.getenv('TR_TORRENT_NAME')
    input_category = ''  # We dont have a category yet
    input_hash = os.getenv('TR_TORRENT_HASH')
    input_id = os.getenv('TR_TORRENT_ID')
    return input_directory, input_name, input_category, input_hash, input_id


def parse_vuze(args):
    # vuze usage: C:\full\path\to\nzbToMedia\TorrentToMedia.py "%D%N%L%I%K%F"
    try:
        input = args[1].split(',')
    except Exception:
        input = []
    try:
        input_directory = os.path.normpath(input[0])
    except Exception:
        input_directory = ''
    try:
        input_name = input[1]
    except Exception:
        input_name = ''
    try:
        input_category = input[2]
    except Exception:
        input_category = ''
    try:
        input_hash = input[3]
    except Exception:
        input_hash = ''
    try:
        input_id = input[3]
    except Exception:
        input_id = ''
    try:
        if input[4] == 'single':
            input_name = input[5]
    except Exception:
        pass

    return input_directory, input_name, input_category, input_hash, input_id


def parse_qbittorrent(args):
    # qbittorrent usage: C:\full\path\to\nzbToMedia\TorrentToMedia.py "%D|%N|%L|%I"
    try:
        input = args[1].split('|')
    except Exception:
        input = []
    try:
        input_directory = os.path.normpath(input[0].replace('"', ''))
    except Exception:
        input_directory = ''
    try:
        input_name = input[1].replace('"', '')
    except Exception:
        input_name = ''
    try:
        input_category = input[2].replace('"', '')
    except Exception:
        input_category = ''
    try:
        input_hash = input[3].replace('"', '')
    except Exception:
        input_hash = ''
    try:
        input_id = input[3].replace('"', '')
    except Exception:
        input_id = ''

    return input_directory, input_name, input_category, input_hash, input_id


def parse_args(client_agent, args):
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
        return clients[client_agent](args)
    except Exception:
        return None, None, None, None, None


def get_dirs(section, subsection, link='hard'):
    to_return = []

    def process_dir(path):
        folders = []

        logger.info("Searching {0} for mediafiles to post-process ...".format(path))
        sync = [o for o in os.listdir(text_type(path)) if os.path.splitext(o)[1] in ['.!sync', '.bts']]
        # search for single files and move them into their own folder for post-processing
        for mediafile in [os.path.join(path, o) for o in os.listdir(text_type(path)) if
                          os.path.isfile(os.path.join(path, o))]:
            if len(sync) > 0:
                break
            if os.path.split(mediafile)[1] in ['Thumbs.db', 'thumbs.db']:
                continue
            try:
                logger.debug("Found file {0} in root directory {1}.".format(os.path.split(mediafile)[1], path))
                new_path = None
                file_ext = os.path.splitext(mediafile)[1]
                try:
                    if file_ext in core.AUDIOCONTAINER:
                        f = beets.mediafile.MediaFile(mediafile)

                        # get artist and album info
                        artist = f.artist
                        album = f.album

                        # create new path
                        new_path = os.path.join(path, "{0} - {1}".format(sanitize_name(artist), sanitize_name(album)))
                    elif file_ext in core.MEDIACONTAINER:
                        f = guessit.guessit(mediafile)

                        # get title
                        title = f.get('series') or f.get('title')

                        if not title:
                            title = os.path.splitext(os.path.basename(mediafile))[0]

                        new_path = os.path.join(path, sanitize_name(title))
                except Exception as e:
                    logger.error("Exception parsing name for media file: {0}: {1}".format(os.path.split(mediafile)[1], e))

                if not new_path:
                    title = os.path.splitext(os.path.basename(mediafile))[0]
                    new_path = os.path.join(path, sanitize_name(title))

                try:
                    new_path = new_path.encode(core.SYS_ENCODING)
                except Exception:
                    pass

                # Just fail-safe incase we already have afile with this clean-name (was actually a bug from earlier code, but let's be safe).
                if os.path.isfile(new_path):
                    new_path2 = os.path.join(os.path.join(os.path.split(new_path)[0], 'new'), os.path.split(new_path)[1])
                    new_path = new_path2

                # create new path if it does not exist
                if not os.path.exists(new_path):
                    make_dir(new_path)

                newfile = os.path.join(new_path, sanitize_name(os.path.split(mediafile)[1]))
                try:
                    newfile = newfile.encode(core.SYS_ENCODING)
                except Exception:
                    pass

                # link file to its new path
                copy_link(mediafile, newfile, link)
            except Exception as e:
                logger.error("Failed to move {0} to its own directory: {1}".format(os.path.split(mediafile)[1], e))

        # removeEmptyFolders(path, removeRoot=False)

        if os.listdir(text_type(path)):
            for dir in [os.path.join(path, o) for o in os.listdir(text_type(path)) if
                        os.path.isdir(os.path.join(path, o))]:
                sync = [o for o in os.listdir(text_type(dir)) if os.path.splitext(o)[1] in ['.!sync', '.bts']]
                if len(sync) > 0 or len(os.listdir(text_type(dir))) == 0:
                    continue
                folders.extend([dir])
        return folders

    try:
        watch_dir = os.path.join(core.CFG[section][subsection]["watch_dir"], subsection)
        if os.path.exists(watch_dir):
            to_return.extend(process_dir(watch_dir))
        elif os.path.exists(core.CFG[section][subsection]["watch_dir"]):
            to_return.extend(process_dir(core.CFG[section][subsection]["watch_dir"]))
    except Exception as e:
        logger.error("Failed to add directories from {0} for post-processing: {1}".format
                     (core.CFG[section][subsection]["watch_dir"], e))

    if core.USELINK == 'move':
        try:
            output_directory = os.path.join(core.OUTPUTDIRECTORY, subsection)
            if os.path.exists(output_directory):
                to_return.extend(process_dir(output_directory))
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


def remove_dir(dir_name):
    logger.info("Deleting {0}".format(dir_name))
    try:
        shutil.rmtree(text_type(dir_name), onerror=onerror)
    except Exception:
        logger.error("Unable to delete folder {0}".format(dir_name))


def clean_dir(path, section, subsection):
    cfg = dict(core.CFG[section][subsection])
    if not os.path.exists(path):
        logger.info('Directory {0} has been processed and removed ...'.format(path), 'CLEANDIR')
        return
    if core.FORCE_CLEAN and not core.FAILED:
        logger.info('Doing Forceful Clean of {0}'.format(path), 'CLEANDIR')
        remove_dir(path)
        return
    min_size = int(cfg.get('minSize', 0))
    delete_ignored = int(cfg.get('delete_ignored', 0))
    try:
        num_files = len(list_media_files(path, min_size=min_size, delete_ignored=delete_ignored))
    except Exception:
        num_files = 'unknown'
    if num_files > 0:
        logger.info(
            "Directory {0} still contains {1} unprocessed file(s), skipping ...".format(path, num_files),
            'CLEANDIRS')
        return

    logger.info("Directory {0} has been processed, removing ...".format(path), 'CLEANDIRS')
    try:
        shutil.rmtree(path, onerror=onerror)
    except Exception:
        logger.error("Unable to delete directory {0}".format(path))


def create_torrent_class(client_agent):
    # Hardlink solution for Torrents
    tc = None

    if client_agent == 'utorrent':
        try:
            logger.debug("Connecting to {0}: {1}".format(client_agent, core.UTORRENTWEBUI))
            tc = UTorrentClient(core.UTORRENTWEBUI, core.UTORRENTUSR, core.UTORRENTPWD)
        except Exception:
            logger.error("Failed to connect to uTorrent")

    if client_agent == 'transmission':
        try:
            logger.debug("Connecting to {0}: http://{1}:{2}".format(
                client_agent, core.TRANSMISSIONHOST, core.TRANSMISSIONPORT))
            tc = TransmissionClient(core.TRANSMISSIONHOST, core.TRANSMISSIONPORT,
                                    core.TRANSMISSIONUSR,
                                    core.TRANSMISSIONPWD)
        except Exception:
            logger.error("Failed to connect to Transmission")

    if client_agent == 'deluge':
        try:
            logger.debug("Connecting to {0}: http://{1}:{2}".format(client_agent, core.DELUGEHOST, core.DELUGEPORT))
            tc = DelugeClient()
            tc.connect(host=core.DELUGEHOST, port=core.DELUGEPORT, username=core.DELUGEUSR,
                       password=core.DELUGEPWD)
        except Exception:
            logger.error("Failed to connect to Deluge")

    if client_agent == 'qbittorrent':
        try:
            logger.debug("Connecting to {0}: http://{1}:{2}".format(client_agent, core.QBITTORRENTHOST, core.QBITTORRENTPORT))
            tc = qBittorrentClient("http://{0}:{1}/".format(core.QBITTORRENTHOST, core.QBITTORRENTPORT))
            tc.login(core.QBITTORRENTUSR, core.QBITTORRENTPWD)
        except Exception:
            logger.error("Failed to connect to qBittorrent")

    return tc


def pause_torrent(client_agent, input_hash, input_id, input_name):
    logger.debug("Stopping torrent {0} in {1} while processing".format(input_name, client_agent))
    try:
        if client_agent == 'utorrent' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.stop(input_hash)
        if client_agent == 'transmission' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.stop_torrent(input_id)
        if client_agent == 'deluge' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.core.pause_torrent([input_id])
        if client_agent == 'qbittorrent' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.pause(input_hash)
        time.sleep(5)
    except Exception:
        logger.warning("Failed to stop torrent {0} in {1}".format(input_name, client_agent))


def resume_torrent(client_agent, input_hash, input_id, input_name):
    if not core.TORRENT_RESUME == 1:
        return
    logger.debug("Starting torrent {0} in {1}".format(input_name, client_agent))
    try:
        if client_agent == 'utorrent' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.start(input_hash)
        if client_agent == 'transmission' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.start_torrent(input_id)
        if client_agent == 'deluge' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.core.resume_torrent([input_id])
        if client_agent == 'qbittorrent' and core.TORRENT_CLASS != "":
            core.TORRENT_CLASS.resume(input_hash)
        time.sleep(5)
    except Exception:
        logger.warning("Failed to start torrent {0} in {1}".format(input_name, client_agent))


def remove_torrent(client_agent, input_hash, input_id, input_name):
    if core.DELETE_ORIGINAL == 1 or core.USELINK == 'move':
        logger.debug("Deleting torrent {0} from {1}".format(input_name, client_agent))
        try:
            if client_agent == 'utorrent' and core.TORRENT_CLASS != "":
                core.TORRENT_CLASS.removedata(input_hash)
                core.TORRENT_CLASS.remove(input_hash)
            if client_agent == 'transmission' and core.TORRENT_CLASS != "":
                core.TORRENT_CLASS.remove_torrent(input_id, True)
            if client_agent == 'deluge' and core.TORRENT_CLASS != "":
                core.TORRENT_CLASS.core.remove_torrent(input_id, True)
            if client_agent == 'qbittorrent' and core.TORRENT_CLASS != "":
                core.TORRENT_CLASS.delete_permanently(input_hash)
            time.sleep(5)
        except Exception:
            logger.warning("Failed to delete torrent {0} in {1}".format(input_name, client_agent))
    else:
        resume_torrent(client_agent, input_hash, input_id, input_name)


def find_download(client_agent, download_id):
    logger.debug("Searching for Download on {0} ...".format(client_agent))
    if client_agent == 'utorrent':
        torrents = core.TORRENT_CLASS.list()[1]['torrents']
        for torrent in torrents:
            if download_id in torrent:
                return True
    if client_agent == 'transmission':
        torrents = core.TORRENT_CLASS.get_torrents()
        for torrent in torrents:
            hash = torrent.hashString
            if hash == download_id:
                return True
    if client_agent == 'deluge':
        return False
    if client_agent == 'qbittorrent':
        torrents = core.TORRENT_CLASS.torrents()
        for torrent in torrents:
            if torrent['hash'] == download_id:
                return True
    if client_agent == 'sabnzbd':
        if "http" in core.SABNZBDHOST:
            base_url = "{0}:{1}/api".format(core.SABNZBDHOST, core.SABNZBDPORT)
        else:
            base_url = "http://{0}:{1}/api".format(core.SABNZBDHOST, core.SABNZBDPORT)
        url = base_url
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


def get_nzoid(input_name):
    nzoid = None
    slots = []
    logger.debug("Searching for nzoid from SAbnzbd ...")
    if "http" in core.SABNZBDHOST:
        base_url = "{0}:{1}/api".format(core.SABNZBDHOST, core.SABNZBDPORT)
    else:
        base_url = "http://{0}:{1}/api".format(core.SABNZBDHOST, core.SABNZBDPORT)
    url = base_url
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
        clean_name = os.path.splitext(os.path.split(input_name)[1])[0]
        slots.extend([(slot['nzo_id'], slot['filename']) for slot in result['queue']['slots']])
    except Exception:
        logger.warning("Data from SABnzbd queue could not be parsed")
    params['mode'] = "history"
    try:
        r = requests.get(url, params=params, verify=False, timeout=(30, 120))
    except requests.ConnectionError:
        logger.error("Unable to open URL")
        return nzoid  # failure
    try:
        result = r.json()
        clean_name = os.path.splitext(os.path.split(input_name)[1])[0]
        slots.extend([(slot['nzo_id'], slot['name']) for slot in result['history']['slots']])
    except Exception:
        logger.warning("Data from SABnzbd history could not be parsed")
    try:
        for nzo_id, name in slots:
            if name in [input_name, clean_name]:
                nzoid = nzo_id
                logger.debug("Found nzoid: {0}".format(nzoid))
                break
    except Exception:
        logger.warning("Data from SABnzbd could not be parsed")
    return nzoid


def clean_file_name(filename):
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


def is_media_file(mediafile, media=True, audio=True, meta=True, archives=True, other=False, otherext=[]):
    file_name, file_ext = os.path.splitext(mediafile)

    try:
        # ignore MAC OS's "resource fork" files
        if file_name.startswith('._'):
            return False
    except Exception:
        pass
    if (media and file_ext.lower() in core.MEDIACONTAINER) \
            or (audio and file_ext.lower() in core.AUDIOCONTAINER) \
            or (meta and file_ext.lower() in core.METACONTAINER) \
            or (archives and is_archive_file(mediafile)) \
            or (other and (file_ext.lower() in otherext or 'all' in otherext)):
        return True
    else:
        return False


def list_media_files(path, min_size=0, delete_ignored=0, media=True, audio=True, meta=True, archives=True, other=False, otherext=[]):
    files = []
    if not os.path.isdir(path):
        if os.path.isfile(path):  # Single file downloads.
            cur_file = os.path.split(path)[1]
            if is_media_file(cur_file, media, audio, meta, archives, other, otherext):
                # Optionally ignore sample files
                if is_sample(path) or not is_min_size(path, min_size):
                    if delete_ignored == 1:
                        try:
                            os.unlink(path)
                            logger.debug('Ignored file {0} has been removed ...'.format
                                         (cur_file))
                        except Exception:
                            pass
                else:
                    files.append(path)

        return files

    for cur_file in os.listdir(text_type(path)):
        full_cur_file = os.path.join(path, cur_file)

        # if it's a folder do it recursively
        if os.path.isdir(full_cur_file) and not cur_file.startswith('.'):
            files += list_media_files(full_cur_file, min_size, delete_ignored, media, audio, meta, archives, other, otherext)

        elif is_media_file(cur_file, media, audio, meta, archives, other, otherext):
            # Optionally ignore sample files
            if is_sample(full_cur_file) or not is_min_size(full_cur_file, min_size):
                if delete_ignored == 1:
                    try:
                        os.unlink(full_cur_file)
                        logger.debug('Ignored file {0} has been removed ...'.format
                                     (cur_file))
                    except Exception:
                        pass
                continue

            files.append(full_cur_file)

    return sorted(files, key=len)


def find_imdbid(dir_name, input_name, omdb_api_key):
    imdbid = None

    logger.info('Attemping imdbID lookup for {0}'.format(input_name))

    # find imdbid in dirName
    logger.info('Searching folder and file names for imdbID ...')
    m = re.search('(tt\d{7})', dir_name + input_name)
    if m:
        imdbid = m.group(1)
        logger.info("Found imdbID [{0}]".format(imdbid))
        return imdbid
    if os.path.isdir(dir_name):
        for file in os.listdir(text_type(dir_name)):
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
        guess = guessit.guessit(input_name)
    except Exception:
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

        if not omdb_api_key:
            logger.info("Unable to determine imdbID: No api key provided for ombdapi.com.")
            return

        logger.debug("Opening URL: {0}".format(url))

        try:
            r = requests.get(url, params={'apikey': omdb_api_key, 'y': year, 't': title},
                             verify=False, timeout=(60, 300))
        except requests.ConnectionError:
            logger.error("Unable to open URL {0}".format(url))
            return

        try:
            results = r.json()
        except Exception:
            logger.error("No json data returned from omdbapi.com")

        try:
            imdbid = results['imdbID']
        except Exception:
            logger.error("No imdbID returned from omdbapi.com")

        if imdbid:
            logger.info("Found imdbID [{0}]".format(imdbid))
            return imdbid

    logger.warning('Unable to find a imdbID for {0}'.format(input_name))
    return imdbid


def extract_files(src, dst=None, keep_archive=None):
    extracted_folder = []
    extracted_archive = []

    for inputFile in list_media_files(src, media=False, audio=False, meta=False, archives=True):
        dir_path = os.path.dirname(inputFile)
        full_file_name = os.path.basename(inputFile)
        archive_name = os.path.splitext(full_file_name)[0]
        archive_name = re.sub(r"part[0-9]+", "", archive_name)

        if dir_path in extracted_folder and archive_name in extracted_archive:
            continue  # no need to extract this, but keep going to look for other archives and sub directories.

        try:
            if extractor.extract(inputFile, dst or dir_path):
                extracted_folder.append(dir_path)
                extracted_archive.append(archive_name)
        except Exception:
            logger.error("Extraction failed for: {0}".format(full_file_name))

    for folder in extracted_folder:
        for inputFile in list_media_files(folder, media=False, audio=False, meta=False, archives=True):
            full_file_name = os.path.basename(inputFile)
            archive_name = os.path.splitext(full_file_name)[0]
            archive_name = re.sub(r"part[0-9]+", "", archive_name)
            if archive_name not in extracted_archive or keep_archive:
                continue  # don't remove if we haven't extracted this archive, or if we want to preserve them.
            logger.info("Removing extracted archive {0} from folder {1} ...".format(full_file_name, folder))
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
    except Exception:
        pass

    languages = set()
    for item in core.SLANGUAGES:
        try:
            languages.add(Language(item))
        except Exception:
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


def server_responding(base_url):
    logger.debug("Attempting to connect to server at {0}".format(base_url), 'SERVER')
    try:
        requests.get(base_url, timeout=(60, 120), verify=False)
        logger.debug("Server responded at {0}".format(base_url), 'SERVER')
        return True
    except (requests.ConnectionError, requests.exceptions.Timeout):
        logger.error("Server failed to respond at {0}".format(base_url), 'SERVER')
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


def backup_versioned_file(old_file, version):
    num_tries = 0

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
            num_tries += 1
            time.sleep(1)
            logger.log(u"Trying again.", logger.DEBUG)

        if num_tries >= 10:
            logger.log(u"Unable to back up {old} to {new} please do it manually.".format(old=old_file, new=new_file), logger.ERROR)
            return False

    return True


def update_download_info_status(input_name, status):
    logger.db("Updating status of our download {0} in the DB to {1}".format(input_name, status))

    my_db = main_db.DBConnection()
    my_db.action("UPDATE downloads SET status=?, last_update=? WHERE input_name=?",
                 [status, datetime.date.today().toordinal(), text_type(input_name)])


def get_download_info(input_name, status):
    logger.db("Getting download info for {0} from the DB".format(input_name))

    my_db = main_db.DBConnection()
    sql_results = my_db.select("SELECT * FROM downloads WHERE input_name=? AND status=?",
                               [text_type(input_name), status])

    return sql_results


class WindowsProcess(object):
    def __init__(self):
        self.mutex = None
        self.mutexname = "nzbtomedia_{pid}".format(pid=core.PID_FILE.replace('\\', '/'))  # {D0E858DF-985E-4907-B7FB-8D732C3FC3B9}"
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
            except Exception:
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
            except Exception:
                pass

        return self.lasterror

    def __del__(self):
        if not self.lasterror:
            if self.lock_socket:
                self.lock_socket.close()
            if os.path.isfile(self.pidpath):
                os.unlink(self.pidpath)


if os.name == 'nt':
    RunningProcess = WindowsProcess
else:
    RunningProcess = PosixProcess
