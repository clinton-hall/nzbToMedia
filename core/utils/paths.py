
from functools import partial
import os
import re
import stat

from six import text_type

import core
from core import logger


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
    return sum([
        (os.path.getsize(f) if os.path.isfile(f) else get_dir_size(f))
        for f in map(prepend, os.listdir(text_type(input_path)))
    ])


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
