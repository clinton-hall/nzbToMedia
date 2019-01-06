# coding=utf-8

from __future__ import print_function, unicode_literals

import os

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
    move_file,
)
from core.utils.identification import find_imdbid
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
    clean_directory,
    flatten_dir,
    get_dir_size,
    make_dir,
    onerror,
    remote_dir,
    remove_dir,
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


def flatten(output_destination):
    return flatten_dir(output_destination, list_media_files(output_destination))


def clean_dir(path, section, subsection):
    cfg = dict(core.CFG[section][subsection])
    min_size = int(cfg.get('minSize', 0))
    delete_ignored = int(cfg.get('delete_ignored', 0))
    try:
        files = list_media_files(path, min_size=min_size, delete_ignored=delete_ignored)
    except Exception:
        files = []
    return clean_directory(path, files)


def process_dir(path, link):
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
            move_file(mediafile, path, link)
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


def get_dirs(section, subsection, link='hard'):
    to_return = []

    watch_directory = core.CFG[section][subsection]['watch_dir']
    directory = os.path.join(watch_directory, subsection)

    if not os.path.exists(directory):
        directory = watch_directory

    try:
        to_return.extend(process_dir(directory, link))
    except Exception as e:
        logger.error('Failed to add directories from {0} for post-processing: {1}'.format(watch_directory, e))

    if core.USELINK == 'move':
        try:
            output_directory = os.path.join(core.OUTPUTDIRECTORY, subsection)
            if os.path.exists(output_directory):
                to_return.extend(process_dir(output_directory, link))
        except Exception as e:
            logger.error('Failed to add directories from {0} for post-processing: {1}'.format(core.OUTPUTDIRECTORY, e))

    if not to_return:
        logger.debug('No directories identified in {0}:{1} for post-processing'.format(section, subsection))

    return list(set(to_return))
