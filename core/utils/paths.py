from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from functools import partial
import os
import re
import shutil
import stat

from six import text_type

import core
from core import logger


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


def make_dir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except Exception:
            return False
    return True


def remote_dir(path):
    if not core.REMOTE_PATHS:
        return path
    for local, remote in core.REMOTE_PATHS:
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
    return sum(
        (os.path.getsize(f) if os.path.isfile(f) else get_dir_size(f))
        for f in map(prepend, os.listdir(text_type(input_path)))
    )


def remove_empty_folders(path, remove_root=True):
    """Remove empty folders."""
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


def flatten_dir(destination, files):
    logger.info('FLATTEN: Flattening directory: {0}'.format(destination))
    for outputFile in files:
        dir_path = os.path.dirname(outputFile)
        file_name = os.path.basename(outputFile)

        if dir_path == destination:
            continue

        target = os.path.join(destination, file_name)

        try:
            shutil.move(outputFile, target)
        except Exception:
            logger.error('Could not flatten {0}'.format(outputFile), 'FLATTEN')

    remove_empty_folders(destination)  # Cleanup empty directories


def clean_directory(path, files):
    if not os.path.exists(path):
        logger.info('Directory {0} has been processed and removed ...'.format(path), 'CLEANDIR')
        return

    if core.FORCE_CLEAN and not core.FAILED:
        logger.info('Doing Forceful Clean of {0}'.format(path), 'CLEANDIR')
        remove_dir(path)
        return

    if files:
        logger.info(
            'Directory {0} still contains {1} unprocessed file(s), skipping ...'.format(path, len(files)),
            'CLEANDIRS',
        )
        return

    logger.info('Directory {0} has been processed, removing ...'.format(path), 'CLEANDIRS')
    try:
        shutil.rmtree(path, onerror=onerror)
    except Exception:
        logger.error('Unable to delete directory {0}'.format(path))


def rchmod(path, mod):
    logger.log('Changing file mode of {0} to {1}'.format(path, oct(mod)))
    os.chmod(path, mod)
    if not os.path.isdir(path):
        return  # Skip files

    for root, dirs, files in os.walk(path):
        for d in dirs:
            os.chmod(os.path.join(root, d), mod)
        for f in files:
            os.chmod(os.path.join(root, f), mod)
