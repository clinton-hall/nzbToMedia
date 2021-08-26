from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
import re

import guessit
import requests
from six import text_type

from core import logger
from core.utils.naming import sanitize_name


def find_imdbid(dir_name, input_name, omdb_api_key):
    imdbid = None

    logger.info('Attemping imdbID lookup for {0}'.format(input_name))

    # find imdbid in dirName
    logger.info('Searching folder and file names for imdbID ...')
    m = re.search(r'\b(tt\d{7,8})\b', dir_name + input_name)
    if m:
        imdbid = m.group(1)
        logger.info('Found imdbID [{0}]'.format(imdbid))
        return imdbid
    if os.path.isdir(dir_name):
        for file in os.listdir(text_type(dir_name)):
            m = re.search(r'\b(tt\d{7,8})\b', file)
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
            logger.info('Unable to determine imdbID: No api key provided for omdbapi.com.')
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


def category_search(input_directory, input_name, input_category, root, categories):
    tordir = False

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
    elif input_name and os.path.isdir(input_directory):
        for file in os.listdir(text_type(input_directory)):
            if os.path.splitext(file)[0] in [input_name, sanitize_name(input_name)]:
                logger.info('SEARCH: Found torrent file {0} in input directory directory {1}'.format(file, input_directory))
                input_directory = os.path.join(input_directory, file)
                logger.info('SEARCH: Setting input_directory to {0}'.format(input_directory))
                input_name = file
                tordir = True
                break

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
