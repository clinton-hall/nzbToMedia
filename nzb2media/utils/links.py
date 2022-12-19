from __future__ import annotations

import logging
import os
import shutil

import linktastic

from nzb2media.utils.paths import make_dir

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

try:
    from jaraco.windows.filesystem import islink, readlink
except ImportError:
    if os.name != 'nt':
        from os.path import islink
        from os import readlink
    else:
        raise


def copy_link(src, target_link, use_link):
    log.info(f'MEDIAFILE: [{os.path.basename(target_link)}]')
    log.info(f'SOURCE FOLDER: [{os.path.dirname(src)}]')
    log.info(f'TARGET FOLDER: [{os.path.dirname(target_link)}]')
    if src != target_link and os.path.exists(target_link):
        log.info('MEDIAFILE already exists in the TARGET folder, skipping ...')
        return True
    if src == target_link and os.path.isfile(target_link) and os.path.isfile(src):
        log.info('SOURCE AND TARGET files are the same, skipping ...')
        return True
    if src == os.path.dirname(target_link):
        log.info('SOURCE AND TARGET folders are the same, skipping ...')
        return True
    make_dir(os.path.dirname(target_link))
    try:
        if use_link == 'dir':
            log.info('Directory linking SOURCE FOLDER -> TARGET FOLDER')
            linktastic.dirlink(src, target_link)
            return True
        if use_link == 'junction':
            log.info('Directory junction linking SOURCE FOLDER -> TARGET FOLDER')
            linktastic.dirlink(src, target_link)
            return True
        if use_link == 'hard':
            log.info('Hard linking SOURCE MEDIAFILE -> TARGET FOLDER')
            linktastic.link(src, target_link)
            return True
        if use_link == 'sym':
            log.info('Sym linking SOURCE MEDIAFILE -> TARGET FOLDER')
            linktastic.symlink(src, target_link)
            return True
        if use_link == 'move-sym':
            log.info('Sym linking SOURCE MEDIAFILE -> TARGET FOLDER')
            shutil.move(src, target_link)
            linktastic.symlink(target_link, src)
            return True
        if use_link == 'move':
            log.info('Moving SOURCE MEDIAFILE -> TARGET FOLDER')
            shutil.move(src, target_link)
            return True
    except Exception as error:
        log.warning(f'Error: {error}, copying instead ... ')
    log.info('Copying SOURCE MEDIAFILE -> TARGET FOLDER')
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
        log.debug(f'{link} is not a link')
    elif link_depth > max_depth or (link_depth == max_depth and islink(target)):
        log.warning(f'Exceeded maximum depth {max_depth} while following link {link}')
    else:
        log.info(f'Changing sym-link: {link} to point directly to file: {target}')
        os.unlink(link)
        linktastic.symlink(target, link)
