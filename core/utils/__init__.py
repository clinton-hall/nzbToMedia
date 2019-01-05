# coding=utf-8

from __future__ import print_function, unicode_literals

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
import requests
from six import text_type
import subliminal

import core
from core import extractor, logger
from core.utils.download_info import get_download_info, update_download_info_status
from core.utils.parsers import (
    parse_args, parse_deluge, parse_other, parse_qbittorrent, parse_rtorrent, parse_transmission,
    parse_utorrent, parse_vuze,
)
from core.utils.paths import get_dir_size, make_dir, remote_dir
from core.utils.processes import RunningProcess
from core.utils.torrents import create_torrent_class, pause_torrent, remove_torrent, resume_torrent

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
    name = re.sub(r'[\\/*]', '-', name)
    name = re.sub(r'[:\'<>|?]', '', name)

    # remove leading/trailing periods and spaces
    name = name.strip(' .')
    try:
        name = name.encode(core.SYS_ENCODING)
    except Exception:
        pass

    return name


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
        logger.debug('SEARCH: Found the Category: {0} in directory structure'.format(input_category))
    elif input_category:
        logger.debug('SEARCH: Could not find the category: {0} in the directory structure'.format(input_category))
    else:
        try:
            input_category = list(set(pathlist) & set(categories))[-1]  # assume last match is most relevant category.
            logger.debug('SEARCH: Found Category: {0} in directory structure'.format(input_category))
        except IndexError:
            input_category = ''
            logger.debug('SEARCH: Could not find a category in the directory structure')
    if not os.path.isdir(input_directory) and os.path.isfile(input_directory):  # If the input directory is a file
        if not input_name:
            input_name = os.path.split(os.path.normpath(input_directory))[1]
        return input_directory, input_name, input_category, root

    if input_category and os.path.isdir(os.path.join(input_directory, input_category)):
        logger.info(
            'SEARCH: Found category directory {0} in input directory directory {1}'.format(input_category, input_directory))
        input_directory = os.path.join(input_directory, input_category)
        logger.info('SEARCH: Setting input_directory to {0}'.format(input_directory))
    if input_name and os.path.isdir(os.path.join(input_directory, input_name)):
        logger.info('SEARCH: Found torrent directory {0} in input directory directory {1}'.format(input_name, input_directory))
        input_directory = os.path.join(input_directory, input_name)
        logger.info('SEARCH: Setting input_directory to {0}'.format(input_directory))
        tordir = True
    elif input_name and os.path.isdir(os.path.join(input_directory, sanitize_name(input_name))):
        logger.info('SEARCH: Found torrent directory {0} in input directory directory {1}'.format(
            sanitize_name(input_name), input_directory))
        input_directory = os.path.join(input_directory, sanitize_name(input_name))
        logger.info('SEARCH: Setting input_directory to {0}'.format(input_directory))
        tordir = True
    elif input_name and os.path.isfile(os.path.join(input_directory, input_name)):
        logger.info('SEARCH: Found torrent file {0} in input directory directory {1}'.format(input_name, input_directory))
        input_directory = os.path.join(input_directory, input_name)
        logger.info('SEARCH: Setting input_directory to {0}'.format(input_directory))
        tordir = True
    elif input_name and os.path.isfile(os.path.join(input_directory, sanitize_name(input_name))):
        logger.info('SEARCH: Found torrent file {0} in input directory directory {1}'.format(
            sanitize_name(input_name), input_directory))
        input_directory = os.path.join(input_directory, sanitize_name(input_name))
        logger.info('SEARCH: Setting input_directory to {0}'.format(input_directory))
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
                logger.info('SEARCH: Found a unique directory {0} in the category directory'.format
                            (pathlist[index + 1]))
                if not input_name:
                    input_name = pathlist[index + 1]
        except ValueError:
            pass

    if input_name and not tordir:
        if input_name in pathlist or sanitize_name(input_name) in pathlist:
            logger.info('SEARCH: Found torrent directory {0} in the directory structure'.format(input_name))
            tordir = True
        else:
            root = 1
    if not tordir:
        root = 2

    if root > 0:
        logger.info('SEARCH: Could not find a unique directory for this download. Assume a common directory.')
        logger.info('SEARCH: We will try and determine which files to process, individually')

    return input_directory, input_name, input_category, root


def is_min_size(input_name, min_size):
    file_name, file_ext = os.path.splitext(os.path.basename(input_name))

    # audio files we need to check directory size not file size
    input_size = os.path.getsize(input_name)
    if file_ext in core.AUDIOCONTAINER:
        try:
            input_size = get_dir_size(os.path.dirname(input_name))
        except Exception:
            logger.error('Failed to get file size for {0}'.format(input_name), 'MINSIZE')
            return True

    # Ignore files under a certain size
    if input_size > min_size * 1048576:
        return True


def is_sample(input_name):
    # Ignore 'sample' in files
    if re.search('(^|[\\W_])sample\\d*[\\W_]', input_name.lower()):
        return True


def copy_link(src, target_link, use_link):
    logger.info('MEDIAFILE: [{0}]'.format(os.path.basename(target_link)), 'COPYLINK')
    logger.info('SOURCE FOLDER: [{0}]'.format(os.path.dirname(src)), 'COPYLINK')
    logger.info('TARGET FOLDER: [{0}]'.format(os.path.dirname(target_link)), 'COPYLINK')

    if src != target_link and os.path.exists(target_link):
        logger.info('MEDIAFILE already exists in the TARGET folder, skipping ...', 'COPYLINK')
        return True
    elif src == target_link and os.path.isfile(target_link) and os.path.isfile(src):
        logger.info('SOURCE AND TARGET files are the same, skipping ...', 'COPYLINK')
        return True
    elif src == os.path.dirname(target_link):
        logger.info('SOURCE AND TARGET folders are the same, skipping ...', 'COPYLINK')
        return True

    make_dir(os.path.dirname(target_link))
    try:
        if use_link == 'dir':
            logger.info('Directory linking SOURCE FOLDER -> TARGET FOLDER', 'COPYLINK')
            linktastic.dirlink(src, target_link)
            return True
        if use_link == 'junction':
            logger.info('Directory junction linking SOURCE FOLDER -> TARGET FOLDER', 'COPYLINK')
            linktastic.dirlink(src, target_link)
            return True
        elif use_link == 'hard':
            logger.info('Hard linking SOURCE MEDIAFILE -> TARGET FOLDER', 'COPYLINK')
            linktastic.link(src, target_link)
            return True
        elif use_link == 'sym':
            logger.info('Sym linking SOURCE MEDIAFILE -> TARGET FOLDER', 'COPYLINK')
            linktastic.symlink(src, target_link)
            return True
        elif use_link == 'move-sym':
            logger.info('Sym linking SOURCE MEDIAFILE -> TARGET FOLDER', 'COPYLINK')
            shutil.move(src, target_link)
            linktastic.symlink(target_link, src)
            return True
        elif use_link == 'move':
            logger.info('Moving SOURCE MEDIAFILE -> TARGET FOLDER', 'COPYLINK')
            shutil.move(src, target_link)
            return True
    except Exception as e:
        logger.warning('Error: {0}, copying instead ... '.format(e), 'COPYLINK')

    logger.info('Copying SOURCE MEDIAFILE -> TARGET FOLDER', 'COPYLINK')
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
        logger.info('Changing sym-link: {0} to point directly to file: {1}'.format(link, target), 'COPYLINK')
        os.unlink(link)
        linktastic.symlink(target, link)


def flatten(output_destination):
    logger.info('FLATTEN: Flattening directory: {0}'.format(output_destination))
    for outputFile in list_media_files(output_destination):
        dir_path = os.path.dirname(outputFile)
        file_name = os.path.basename(outputFile)

        if dir_path == output_destination:
            continue

        target = os.path.join(output_destination, file_name)

        try:
            shutil.move(outputFile, target)
        except Exception:
            logger.error('Could not flatten {0}'.format(outputFile), 'FLATTEN')

    remove_empty_folders(output_destination)  # Cleanup empty directories


def remove_empty_folders(path, remove_root=True):
    """Function to remove empty folders"""
    if not os.path.isdir(path):
        return

    # remove empty subfolders
    logger.debug('Checking for empty folders in:{0}'.format(path))
    files = os.listdir(text_type(path))
    if len(files):
        for f in files:
            fullpath = os.path.join(path, f)
            if os.path.isdir(fullpath):
                remove_empty_folders(fullpath)

    # if folder empty, delete it
    files = os.listdir(text_type(path))
    if len(files) == 0 and remove_root:
        logger.debug('Removing empty folder:{}'.format(path))
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

    # Build the Wake-On-LAN 'Magic Packet'...

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
        return 'Up'
    except Exception:
        return 'Down'


def wake_up():
    host = core.CFG['WakeOnLan']['host']
    port = int(core.CFG['WakeOnLan']['port'])
    mac = core.CFG['WakeOnLan']['mac']

    i = 1
    while test_connection(host, port) == 'Down' and i < 4:
        logger.info(('Sending WakeOnLan Magic Packet for mac: {0}'.format(mac)))
        wake_on_lan(mac)
        time.sleep(20)
        i = i + 1

    if test_connection(host, port) == 'Down':  # final check.
        logger.warning('System with mac: {0} has not woken after 3 attempts. '
                       'Continuing with the rest of the script.'.format(mac))
    else:
        logger.info('System with mac: {0} has been woken. Continuing with the rest of the script.'.format(mac))


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

    ascii_convert = int(core.CFG['ASCII']['convert'])
    if ascii_convert == 0 or os.name == 'nt':  # just return if we don't want to convert or on windows os and '\' is replaced!.
        return input_name, dir_name

    encoded, input_name = char_replace(input_name)

    directory, base = os.path.split(dir_name)
    if not base:  # ended with '/'
        directory, base = os.path.split(directory)

    encoded, base2 = char_replace(base)
    if encoded:
        dir_name = os.path.join(directory, base2)
        logger.info('Renaming directory to: {0}.'.format(base2), 'ENCODER')
        os.rename(os.path.join(directory, base), dir_name)
        if 'NZBOP_SCRIPTDIR' in os.environ:
            print('[NZB] DIRECTORY={0}'.format(dir_name))

    for dirname, dirnames, filenames in os.walk(dir_name, topdown=False):
        for subdirname in dirnames:
            encoded, subdirname2 = char_replace(subdirname)
            if encoded:
                logger.info('Renaming directory to: {0}.'.format(subdirname2), 'ENCODER')
                os.rename(os.path.join(dirname, subdirname), os.path.join(dirname, subdirname2))

    for dirname, dirnames, filenames in os.walk(dir_name):
        for filename in filenames:
            encoded, filename2 = char_replace(filename)
            if encoded:
                logger.info('Renaming file to: {0}.'.format(filename2), 'ENCODER')
                os.rename(os.path.join(dirname, filename), os.path.join(dirname, filename2))

    return input_name, dir_name


def get_dirs(section, subsection, link='hard'):
    to_return = []

    def process_dir(path):
        folders = []

        logger.info('Searching {0} for mediafiles to post-process ...'.format(path))
        sync = [o for o in os.listdir(text_type(path)) if os.path.splitext(o)[1] in ['.!sync', '.bts']]
        # search for single files and move them into their own folder for post-processing
        for mediafile in [os.path.join(path, o) for o in os.listdir(text_type(path)) if
                          os.path.isfile(os.path.join(path, o))]:
            if len(sync) > 0:
                break
            if os.path.split(mediafile)[1] in ['Thumbs.db', 'thumbs.db']:
                continue
            try:
                logger.debug('Found file {0} in root directory {1}.'.format(os.path.split(mediafile)[1], path))
                new_path = None
                file_ext = os.path.splitext(mediafile)[1]
                try:
                    if file_ext in core.AUDIOCONTAINER:
                        f = beets.mediafile.MediaFile(mediafile)

                        # get artist and album info
                        artist = f.artist
                        album = f.album

                        # create new path
                        new_path = os.path.join(path, '{0} - {1}'.format(sanitize_name(artist), sanitize_name(album)))
                    elif file_ext in core.MEDIACONTAINER:
                        f = guessit.guessit(mediafile)

                        # get title
                        title = f.get('series') or f.get('title')

                        if not title:
                            title = os.path.splitext(os.path.basename(mediafile))[0]

                        new_path = os.path.join(path, sanitize_name(title))
                except Exception as e:
                    logger.error('Exception parsing name for media file: {0}: {1}'.format(os.path.split(mediafile)[1], e))

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
                logger.error('Failed to move {0} to its own directory: {1}'.format(os.path.split(mediafile)[1], e))

        # removeEmptyFolders(path, removeRoot=False)

        if os.listdir(text_type(path)):
            for directory in [os.path.join(path, o) for o in os.listdir(text_type(path)) if
                              os.path.isdir(os.path.join(path, o))]:
                sync = [o for o in os.listdir(text_type(directory)) if os.path.splitext(o)[1] in ['.!sync', '.bts']]
                if len(sync) > 0 or len(os.listdir(text_type(directory))) == 0:
                    continue
                folders.extend([directory])
        return folders

    try:
        watch_dir = os.path.join(core.CFG[section][subsection]['watch_dir'], subsection)
        if os.path.exists(watch_dir):
            to_return.extend(process_dir(watch_dir))
        elif os.path.exists(core.CFG[section][subsection]['watch_dir']):
            to_return.extend(process_dir(core.CFG[section][subsection]['watch_dir']))
    except Exception as e:
        logger.error('Failed to add directories from {0} for post-processing: {1}'.format
                     (core.CFG[section][subsection]['watch_dir'], e))

    if core.USELINK == 'move':
        try:
            output_directory = os.path.join(core.OUTPUTDIRECTORY, subsection)
            if os.path.exists(output_directory):
                to_return.extend(process_dir(output_directory))
        except Exception as e:
            logger.error('Failed to add directories from {0} for post-processing: {1}'.format(core.OUTPUTDIRECTORY, e))

    if not to_return:
        logger.debug('No directories identified in {0}:{1} for post-processing'.format(section, subsection))

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
    logger.info('Deleting {0}'.format(dir_name))
    try:
        shutil.rmtree(text_type(dir_name), onerror=onerror)
    except Exception:
        logger.error('Unable to delete folder {0}'.format(dir_name))


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
            'Directory {0} still contains {1} unprocessed file(s), skipping ...'.format(path, num_files),
            'CLEANDIRS')
        return

    logger.info('Directory {0} has been processed, removing ...'.format(path), 'CLEANDIRS')
    try:
        shutil.rmtree(path, onerror=onerror)
    except Exception:
        logger.error('Unable to delete directory {0}'.format(path))


def find_download(client_agent, download_id):
    logger.debug('Searching for Download on {0} ...'.format(client_agent))
    if client_agent == 'utorrent':
        torrents = core.TORRENT_CLASS.list()[1]['torrents']
        for torrent in torrents:
            if download_id in torrent:
                return True
    if client_agent == 'transmission':
        torrents = core.TORRENT_CLASS.get_torrents()
        for torrent in torrents:
            torrent_hash = torrent.hashString
            if torrent_hash == download_id:
                return True
    if client_agent == 'deluge':
        return False
    if client_agent == 'qbittorrent':
        torrents = core.TORRENT_CLASS.torrents()
        for torrent in torrents:
            if torrent['hash'] == download_id:
                return True
    if client_agent == 'sabnzbd':
        if 'http' in core.SABNZBDHOST:
            base_url = '{0}:{1}/api'.format(core.SABNZBDHOST, core.SABNZBDPORT)
        else:
            base_url = 'http://{0}:{1}/api'.format(core.SABNZBDHOST, core.SABNZBDPORT)
        url = base_url
        params = {
            'apikey': core.SABNZBDAPIKEY,
            'mode': 'get_files',
            'output': 'json',
            'value': download_id,
        }
        try:
            r = requests.get(url, params=params, verify=False, timeout=(30, 120))
        except requests.ConnectionError:
            logger.error('Unable to open URL')
            return False  # failure

        result = r.json()
        if result['files']:
            return True
    return False


def clean_file_name(filename):
    """Cleans up nzb name by removing any . and _
    characters, along with any trailing hyphens.

    Is basically equivalent to replacing all _ and . with a
    space, but handles decimal numbers in string, for example:
    """

    filename = re.sub(r'(\D)\.(?!\s)(\D)', r'\1 \2', filename)
    filename = re.sub(r'(\d)\.(\d{4})', r'\1 \2', filename)  # if it ends in a year then don't keep the dot
    filename = re.sub(r'(\D)\.(?!\s)', r'\1 ', filename)
    filename = re.sub(r'\.(?!\s)(\D)', r' \1', filename)
    filename = filename.replace('_', ' ')
    filename = re.sub('-$', '', filename)
    filename = re.sub(r'^\[.*]', '', filename)
    return filename.strip()


def is_archive_file(filename):
    """Check if the filename is allowed for the Archive"""
    for regext in core.COMPRESSEDCONTAINER:
        if regext.search(filename):
            return regext.split(filename)[0]
    return False


def is_media_file(mediafile, media=True, audio=True, meta=True, archives=True, other=False, otherext=None):
    if otherext is None:
        otherext = []

    file_name, file_ext = os.path.splitext(mediafile)

    try:
        # ignore MAC OS's 'resource fork' files
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


def list_media_files(path, min_size=0, delete_ignored=0, media=True, audio=True, meta=True, archives=True, other=False, otherext=None):
    if otherext is None:
        otherext = []

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
    m = re.search(r'(tt\d{7})', dir_name + input_name)
    if m:
        imdbid = m.group(1)
        logger.info('Found imdbID [{0}]'.format(imdbid))
        return imdbid
    if os.path.isdir(dir_name):
        for file in os.listdir(text_type(dir_name)):
            m = re.search(r'(tt\d{7})', file)
            if m:
                imdbid = m.group(1)
                logger.info('Found imdbID [{0}] via file name'.format(imdbid))
                return imdbid
    if 'NZBPR__DNZB_MOREINFO' in os.environ:
        dnzb_more_info = os.environ.get('NZBPR__DNZB_MOREINFO', '')
        if dnzb_more_info != '':
            regex = re.compile(r'^http://www.imdb.com/title/(tt[0-9]+)/$', re.IGNORECASE)
            m = regex.match(dnzb_more_info)
            if m:
                imdbid = m.group(1)
                logger.info('Found imdbID [{0}] from DNZB-MoreInfo'.format(imdbid))
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

        url = 'http://www.omdbapi.com'

        if not omdb_api_key:
            logger.info('Unable to determine imdbID: No api key provided for ombdapi.com.')
            return

        logger.debug('Opening URL: {0}'.format(url))

        try:
            r = requests.get(url, params={'apikey': omdb_api_key, 'y': year, 't': title},
                             verify=False, timeout=(60, 300))
        except requests.ConnectionError:
            logger.error('Unable to open URL {0}'.format(url))
            return

        try:
            results = r.json()
        except Exception:
            logger.error('No json data returned from omdbapi.com')

        try:
            imdbid = results['imdbID']
        except Exception:
            logger.error('No imdbID returned from omdbapi.com')

        if imdbid:
            logger.info('Found imdbID [{0}]'.format(imdbid))
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
        archive_name = re.sub(r'part[0-9]+', '', archive_name)

        if dir_path in extracted_folder and archive_name in extracted_archive:
            continue  # no need to extract this, but keep going to look for other archives and sub directories.

        try:
            if extractor.extract(inputFile, dst or dir_path):
                extracted_folder.append(dir_path)
                extracted_archive.append(archive_name)
        except Exception:
            logger.error('Extraction failed for: {0}'.format(full_file_name))

    for folder in extracted_folder:
        for inputFile in list_media_files(folder, media=False, audio=False, meta=False, archives=True):
            full_file_name = os.path.basename(inputFile)
            archive_name = os.path.splitext(full_file_name)[0]
            archive_name = re.sub(r'part[0-9]+', '', archive_name)
            if archive_name not in extracted_archive or keep_archive:
                continue  # don't remove if we haven't extracted this archive, or if we want to preserve them.
            logger.info('Removing extracted archive {0} from folder {1} ...'.format(full_file_name, folder))
            try:
                if not os.access(inputFile, os.W_OK):
                    os.chmod(inputFile, stat.S_IWUSR)
                os.remove(inputFile)
                time.sleep(1)
            except Exception as e:
                logger.error('Unable to remove file {0} due to: {1}'.format(inputFile, e))


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

    logger.info('Attempting to download subtitles for {0}'.format(filename), 'SUBTITLES')
    try:
        video = subliminal.scan_video(filename)
        subtitles = subliminal.download_best_subtitles({video}, languages)
        subliminal.save_subtitles(video, subtitles[video])
    except Exception as e:
        logger.error('Failed to download subtitles for {0} due to: {1}'.format(filename, e), 'SUBTITLES')


def server_responding(base_url):
    logger.debug('Attempting to connect to server at {0}'.format(base_url), 'SERVER')
    try:
        requests.get(base_url, timeout=(60, 120), verify=False)
        logger.debug('Server responded at {0}'.format(base_url), 'SERVER')
        return True
    except (requests.ConnectionError, requests.exceptions.Timeout):
        logger.error('Server failed to respond at {0}'.format(base_url), 'SERVER')
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
    logger.debug('Attempting to update Plex Library for category {0}.'.format(category), 'PLEX')
    for item in core.PLEXSEC:
        if item[0] == category:
            section = item[1]

    if section:
        url = '{url}{section}/refresh?X-Plex-Token={token}'.format(url=url, section=section, token=core.PLEXTOKEN)
        requests.get(url, timeout=(60, 120), verify=False)
        logger.debug('Plex Library has been refreshed.', 'PLEX')
    else:
        logger.debug('Could not identify section for plex update', 'PLEX')


def backup_versioned_file(old_file, version):
    num_tries = 0

    new_file = '{old}.v{version}'.format(old=old_file, version=version)

    while not os.path.isfile(new_file):
        if not os.path.isfile(old_file):
            logger.log(u'Not creating backup, {file} doesn\'t exist'.format(file=old_file), logger.DEBUG)
            break

        try:
            logger.log(u'Trying to back up {old} to {new]'.format(old=old_file, new=new_file), logger.DEBUG)
            shutil.copy(old_file, new_file)
            logger.log(u'Backup done', logger.DEBUG)
            break
        except Exception as error:
            logger.log(u'Error while trying to back up {old} to {new} : {msg}'.format
                       (old=old_file, new=new_file, msg=error), logger.WARNING)
            num_tries += 1
            time.sleep(1)
            logger.log(u'Trying again.', logger.DEBUG)

        if num_tries >= 10:
            logger.log(u'Unable to back up {old} to {new} please do it manually.'.format(old=old_file, new=new_file), logger.ERROR)
            return False

    return True
