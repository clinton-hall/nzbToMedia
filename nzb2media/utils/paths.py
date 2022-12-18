from __future__ import annotations

import logging
import os
import re
import shutil
import stat
from functools import partial

import nzb2media

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


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
    log.info(f'Deleting {dir_name}')
    try:
        shutil.rmtree(dir_name, onerror=onerror)
    except Exception:
        log.error(f'Unable to delete folder {dir_name}')


def make_dir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except Exception:
            return False
    return True


def remote_dir(path):
    if not nzb2media.REMOTE_PATHS:
        return path
    for local, remote in nzb2media.REMOTE_PATHS:
        if local in path:
            base_dirs = path.replace(local, '').split(os.sep)
            if '/' in remote:
                remote_sep = '/'
            else:
                remote_sep = '\\'
            new_path = remote_sep.join([remote] + base_dirs)
            new_path = re.sub(r'(\S)(\\+)', r'\1\\', new_path)
            new_path = re.sub(r'(/+)', r'/', new_path)
            new_path = re.sub(r'([/\\])$', r'', new_path)
            return new_path
    return path


def get_dir_size(input_path):
    prepend = partial(os.path.join, input_path)
    return sum((os.path.getsize(f) if os.path.isfile(f) else get_dir_size(f)) for f in map(prepend, os.listdir(input_path)))


def remove_empty_folders(path, remove_root=True):
    """Remove empty folders."""
    if not os.path.isdir(path):
        return
    # remove empty subfolders
    log.debug(f'Checking for empty folders in:{path}')
    files = os.listdir(path)
    if len(files):
        for each_file in files:
            fullpath = os.path.join(path, each_file)
            if os.path.isdir(fullpath):
                remove_empty_folders(fullpath)
    # if folder empty, delete it
    files = os.listdir(path)
    if len(files) == 0 and remove_root:
        log.debug(f'Removing empty folder:{path}')
        os.rmdir(path)


def remove_read_only(filename):
    if os.path.isfile(filename):
        # check first the read-only attribute
        file_attribute = os.stat(filename)[0]
        if not file_attribute & stat.S_IWRITE:
            # File is read-only, so make it writeable
            log.debug(f'Read only mode on file {filename}. Attempting to make it writeable')
            try:
                os.chmod(filename, stat.S_IWRITE)
            except Exception:
                log.warning(f'Cannot change permissions of {filename}')


def flatten_dir(destination, files):
    log.info(f'FLATTEN: Flattening directory: {destination}')
    for output_file in files:
        dir_path = os.path.dirname(output_file)
        file_name = os.path.basename(output_file)
        if dir_path == destination:
            continue
        target = os.path.join(destination, file_name)
        try:
            shutil.move(output_file, target)
        except Exception:
            log.error(f'Could not flatten {output_file}')
    remove_empty_folders(destination)  # Cleanup empty directories


def clean_directory(path, files):
    if not os.path.exists(path):
        log.info(f'Directory {path} has been processed and removed ...')
        return
    if nzb2media.FORCE_CLEAN and not nzb2media.FAILED:
        log.info(f'Doing Forceful Clean of {path}')
        remove_dir(path)
        return
    if files:
        log.info(f'Directory {path} still contains {len(files)} unprocessed file(s), skipping ...')
        return
    log.info(f'Directory {path} has been processed, removing ...')
    try:
        shutil.rmtree(path, onerror=onerror)
    except Exception:
        log.error(f'Unable to delete directory {path}')


def rchmod(path, mod):
    log.info(f'Changing file mode of {path} to {oct(mod)}')
    os.chmod(path, mod)
    if not os.path.isdir(path):
        return  # Skip files
    for root, dirs, files in os.walk(path):
        for each_dir in dirs:
            os.chmod(os.path.join(root, each_dir), mod)
        for each_file in files:
            os.chmod(os.path.join(root, each_file), mod)
