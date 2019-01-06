# coding=utf-8

from __future__ import print_function, unicode_literals

import os
import re
import shutil
import stat

import beets
import guessit
import requests
from six import text_type

import core
from core import logger
from core.utils import shutil_custom
from core.utils.download_info import get_download_info, update_download_info_status
from core.utils.encoding import char_replace, convert_to_ascii
from core.utils.files import (
    backup_versioned_file,
    extract_files,
    is_archive_file,
    is_media_file,
    is_min_size,
    list_media_files,
)
from core.utils.links import copy_link, replace_links
from core.utils.naming import clean_file_name, is_sample, sanitize_name
from core.utils.network import find_download, test_connection, wake_on_lan, wake_up
from core.utils.notifications import plex_update
from core.utils.nzbs import get_nzoid, report_nzb
from core.utils.parsers import (
    parse_args,
    parse_deluge,
    parse_other,
    parse_qbittorrent,
    parse_rtorrent,
    parse_transmission,
    parse_utorrent,
    parse_vuze,
)
from core.utils.paths import (
    get_dir_size, make_dir,
    remote_dir,
    remove_empty_folders,
    remove_read_only,
)
from core.utils.processes import RunningProcess
from core.utils.subtitles import import_subs
from core.utils.torrents import create_torrent_class, pause_torrent, remove_torrent, resume_torrent

try:
    import jaraco
except ImportError:
    if os.name == 'nt':
        raise

requests.packages.urllib3.disable_warnings()

shutil_custom.monkey_patch()


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


def server_responding(base_url):
    logger.debug('Attempting to connect to server at {0}'.format(base_url), 'SERVER')
    try:
        requests.get(base_url, timeout=(60, 120), verify=False)
        logger.debug('Server responded at {0}'.format(base_url), 'SERVER')
        return True
    except (requests.ConnectionError, requests.exceptions.Timeout):
        logger.error('Server failed to respond at {0}'.format(base_url), 'SERVER')
        return False
