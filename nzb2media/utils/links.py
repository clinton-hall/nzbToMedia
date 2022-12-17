from __future__ import annotations

import os
import shutil

import linktastic

from nzb2media.utils.paths import make_dir

try:
    from jaraco.windows.filesystem import islink, readlink
except ImportError:
    if os.name == 'nt':
        raise
    else:
        from os.path import islink
        from os import readlink


def copy_link(src, target_link, use_link):
    logger.info(f'MEDIAFILE: [{os.path.basename(target_link)}]', 'COPYLINK')
    logger.info(f'SOURCE FOLDER: [{os.path.dirname(src)}]', 'COPYLINK')
    logger.info(f'TARGET FOLDER: [{os.path.dirname(target_link)}]', 'COPYLINK')

    if src != target_link and os.path.exists(target_link):
        logger.info(
            'MEDIAFILE already exists in the TARGET folder, skipping ...',
            'COPYLINK',
        )
        return True
    elif (
        src == target_link
        and os.path.isfile(target_link)
        and os.path.isfile(src)
    ):
        logger.info(
            'SOURCE AND TARGET files are the same, skipping ...', 'COPYLINK',
        )
        return True
    elif src == os.path.dirname(target_link):
        logger.info(
            'SOURCE AND TARGET folders are the same, skipping ...', 'COPYLINK',
        )
        return True

    make_dir(os.path.dirname(target_link))
    try:
        if use_link == 'dir':
            logger.info(
                'Directory linking SOURCE FOLDER -> TARGET FOLDER', 'COPYLINK',
            )
            linktastic.dirlink(src, target_link)
            return True
        if use_link == 'junction':
            logger.info(
                'Directory junction linking SOURCE FOLDER -> TARGET FOLDER',
                'COPYLINK',
            )
            linktastic.dirlink(src, target_link)
            return True
        elif use_link == 'hard':
            logger.info(
                'Hard linking SOURCE MEDIAFILE -> TARGET FOLDER', 'COPYLINK',
            )
            linktastic.link(src, target_link)
            return True
        elif use_link == 'sym':
            logger.info(
                'Sym linking SOURCE MEDIAFILE -> TARGET FOLDER', 'COPYLINK',
            )
            linktastic.symlink(src, target_link)
            return True
        elif use_link == 'move-sym':
            logger.info(
                'Sym linking SOURCE MEDIAFILE -> TARGET FOLDER', 'COPYLINK',
            )
            shutil.move(src, target_link)
            linktastic.symlink(target_link, src)
            return True
        elif use_link == 'move':
            logger.info('Moving SOURCE MEDIAFILE -> TARGET FOLDER', 'COPYLINK')
            shutil.move(src, target_link)
            return True
    except Exception as e:
        logger.warning(f'Error: {e}, copying instead ... ', 'COPYLINK')

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
        logger.debug(f'{link} is not a link')
    elif link_depth > max_depth or (
        link_depth == max_depth and islink(target)
    ):
        logger.warning(
            f'Exceeded maximum depth {max_depth} while following link {link}',
        )
    else:
        logger.info(
            f'Changing sym-link: {link} to point directly to file: {target}',
            'COPYLINK',
        )
        os.unlink(link)
        linktastic.symlink(target, link)
