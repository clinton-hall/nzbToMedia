from __future__ import annotations

import logging
import os.path
import urllib.parse

import nzb2media
from nzb2media.utils.files import list_media_files
from nzb2media.utils.files import move_file
from nzb2media.utils.paths import clean_directory
from nzb2media.utils.paths import flatten_dir

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def flatten(output_destination):
    return flatten_dir(output_destination, list_media_files(output_destination))


def clean_dir(path, section, subsection):
    cfg = dict(nzb2media.CFG[section][subsection])
    min_size = int(cfg.get('minSize', 0))
    delete_ignored = int(cfg.get('delete_ignored', 0))
    try:
        files = list_media_files(path, min_size=min_size, delete_ignored=delete_ignored)
    except Exception:
        files = []
    return clean_directory(path, files)


def process_dir(path, link):
    folders = []
    log.info(f'Searching {path} for mediafiles to post-process ...')
    dir_contents = os.listdir(path)
    # search for single files and move them into their own folder for post-processing
    # Generate list of sync files
    sync_files = (item for item in dir_contents if os.path.splitext(item)[1] in {'.!sync', '.bts'})
    # Generate a list of file paths
    filepaths = (os.path.join(path, item) for item in dir_contents if item not in {'Thumbs.db', 'thumbs.db'})
    # Generate a list of media files
    mediafiles = (item for item in filepaths if os.path.isfile(item))
    if not any(sync_files):
        for mediafile in mediafiles:
            try:
                move_file(mediafile, path, link)
            except Exception as error:
                log.error(f'Failed to move {os.path.split(mediafile)[1]} to its own directory: {error}')
    # removeEmptyFolders(path, removeRoot=False)
    # Generate all path contents
    path_contents = (os.path.join(path, item) for item in os.listdir(path))
    # Generate all directories from path contents
    directories = (path for path in path_contents if os.path.isdir(path))
    for directory in directories:
        dir_contents = os.listdir(directory)
        sync_files = (item for item in dir_contents if os.path.splitext(item)[1] in {'.!sync', '.bts'})
        if not any(dir_contents) or any(sync_files):
            continue
        folders.append(directory)
    return folders


def get_dirs(section, subsection, link='hard'):
    to_return = []
    watch_directory = nzb2media.CFG[section][subsection]['watch_dir']
    directory = os.path.join(watch_directory, subsection)
    if not os.path.exists(directory):
        directory = watch_directory
    try:
        to_return.extend(process_dir(directory, link))
    except Exception as error:
        log.error(f'Failed to add directories from {watch_directory} for post-processing: {error}')
    if nzb2media.USE_LINK == 'move':
        try:
            output_directory = os.path.join(nzb2media.OUTPUT_DIRECTORY, subsection)
            if os.path.exists(output_directory):
                to_return.extend(process_dir(output_directory, link))
        except Exception as error:
            log.error(f'Failed to add directories from {nzb2media.OUTPUT_DIRECTORY} for post-processing: {error}')
    if not to_return:
        log.debug(f'No directories identified in {section}:{subsection} for post-processing')
    return list(set(to_return))


def create_url(scheme: str, host: str, port: int | None = None, path: str = '', query: str = '') -> str:
    """Create a url from its component parts."""
    netloc = host if port is None else f'{host}:{port}'
    fragments = ''
    return urllib.parse.urlunsplit([scheme, netloc, path, query, fragments])
