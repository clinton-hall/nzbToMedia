from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
import shutil

import linktastic

from core import logger
from core.utils.paths import make_dir

try:
    from jaraco.windows.filesystem import islink, readlink
except ImportError:
    if os.name == 'nt':
        raise
    else:
        from os.path import islink
        from os import readlink


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


def replace_links(link, max_depth=10):
    link_depth = 0
    target = link

    for attempt in range(0, max_depth):
        if not islink(target):
            break
        target = readlink(target)
        link_depth = attempt

    if not link_depth:
        logger.debug('{0} is not a link'.format(link))
    elif link_depth > max_depth or (link_depth == max_depth and islink(target)):
        logger.warning('Exceeded maximum depth {0} while following link {1}'.format(max_depth, link))
    else:
        logger.info('Changing sym-link: {0} to point directly to file: {1}'.format(link, target), 'COPYLINK')
        os.unlink(link)
        linktastic.symlink(target, link)
