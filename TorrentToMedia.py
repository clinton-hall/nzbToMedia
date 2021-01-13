#!/usr/bin/env python
# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import datetime
import os
import sys

import eol
import cleanup
eol.check()
cleanup.clean(cleanup.FOLDER_STRUCTURE)

import core
from core import logger, main_db
from core.auto_process import comics, games, movies, music, tv, books
from core.auto_process.common import ProcessResult
from core.plugins.plex import plex_update
from core.user_scripts import external_script
from core.utils import char_replace, convert_to_ascii, replace_links

try:
    text_type = unicode
except NameError:
    text_type = str


def process_torrent(input_directory, input_name, input_category, input_hash, input_id, client_agent):
    status = 1  # 1 = failed | 0 = success
    root = 0
    found_file = 0

    if client_agent != 'manual' and not core.DOWNLOAD_INFO:
        logger.debug('Adding TORRENT download info for directory {0} to database'.format(input_directory))

        my_db = main_db.DBConnection()

        input_directory1 = input_directory
        input_name1 = input_name

        try:
            encoded, input_directory1 = char_replace(input_directory)
            encoded, input_name1 = char_replace(input_name)
        except Exception:
            pass

        control_value_dict = {'input_directory': text_type(input_directory1)}
        new_value_dict = {
            'input_name': text_type(input_name1),
            'input_hash': text_type(input_hash),
            'input_id': text_type(input_id),
            'client_agent': text_type(client_agent),
            'status': 0,
            'last_update': datetime.date.today().toordinal(),
        }
        my_db.upsert('downloads', new_value_dict, control_value_dict)

    logger.debug('Received Directory: {0} | Name: {1} | Category: {2}'.format(input_directory, input_name, input_category))

    # Confirm the category by parsing directory structure
    input_directory, input_name, input_category, root = core.category_search(input_directory, input_name, input_category,
                                                                             root, core.CATEGORIES)
    if input_category == '':
        input_category = 'UNCAT'

    usercat = input_category

    logger.debug('Determined Directory: {0} | Name: {1} | Category: {2}'.format
                 (input_directory, input_name, input_category))

    # auto-detect section
    section = core.CFG.findsection(input_category).isenabled()
    if section is None: #Check for user_scripts for 'ALL' and 'UNCAT'
        if usercat in core.CATEGORIES:
            section = core.CFG.findsection('ALL').isenabled()
            usercat = 'ALL'
        else:
            section = core.CFG.findsection('UNCAT').isenabled()
            usercat = 'UNCAT'
    if section is None: # We haven't found any categories to process.
        logger.error('Category:[{0}] is not defined or is not enabled. '
                     'Please rename it or ensure it is enabled for the appropriate section '
                     'in your autoProcessMedia.cfg and try again.'.format
                     (input_category))
        return [-1, '']

    if len(section) > 1:
        logger.error('Category:[{0}] is not unique, {1} are using it. '
                     'Please rename it or disable all other sections using the same category name '
                     'in your autoProcessMedia.cfg and try again.'.format
                     (usercat, section.keys()))
        return [-1, '']

    if section:
        section_name = section.keys()[0]
        logger.info('Auto-detected SECTION:{0}'.format(section_name))
    else:
        logger.error('Unable to locate a section with subsection:{0} '
                     'enabled in your autoProcessMedia.cfg, exiting!'.format
                     (input_category))
        return [-1, '']

    section = dict(section[section_name][usercat])  # Type cast to dict() to allow effective usage of .get()

    torrent_no_link = int(section.get('Torrent_NoLink', 0))
    keep_archive = int(section.get('keep_archive', 0))
    extract = int(section.get('extract', 0))
    extensions = section.get('user_script_mediaExtensions', '')
    unique_path = int(section.get('unique_path', 1))

    if client_agent != 'manual':
        core.pause_torrent(client_agent, input_hash, input_id, input_name)

    # In case input is not directory, make sure to create one.
    # This way Processing is isolated.
    if not os.path.isdir(os.path.join(input_directory, input_name)):
        basename = os.path.basename(input_directory)
        basename = core.sanitize_name(input_name) \
            if input_name == basename else os.path.splitext(core.sanitize_name(input_name))[0]
        output_destination = os.path.join(core.OUTPUT_DIRECTORY, input_category, basename)
    elif unique_path:
        output_destination = os.path.normpath(
            core.os.path.join(core.OUTPUT_DIRECTORY, input_category, core.sanitize_name(input_name).replace(' ', '.')))
    else:
        output_destination = os.path.normpath(
            core.os.path.join(core.OUTPUT_DIRECTORY, input_category))

    if output_destination in input_directory:
        output_destination = input_directory

    logger.info('Output directory set to: {0}'.format(output_destination))

    if core.SAFE_MODE and output_destination == core.TORRENT_DEFAULT_DIRECTORY:
        logger.error('The output directory:[{0}] is the Download Directory. '
                     'Edit outputDirectory in autoProcessMedia.cfg. Exiting'.format
                     (input_directory))
        return [-1, '']

    logger.debug('Scanning files in directory: {0}'.format(input_directory))

    if section_name in ['HeadPhones', 'Lidarr']:
        core.NOFLATTEN.extend(
            input_category)  # Make sure we preserve folder structure for HeadPhones.

    now = datetime.datetime.now()

    if extract == 1:
        input_files = core.list_media_files(input_directory, archives=False, other=True, otherext=extensions)
    else:
        input_files = core.list_media_files(input_directory, other=True, otherext=extensions)
    if len(input_files) == 0 and os.path.isfile(input_directory):
        input_files = [input_directory]
        logger.debug('Found 1 file to process: {0}'.format(input_directory))
    else:
        logger.debug('Found {0} files in {1}'.format(len(input_files), input_directory))
    for inputFile in input_files:
        file_path = os.path.dirname(inputFile)
        file_name, file_ext = os.path.splitext(os.path.basename(inputFile))
        full_file_name = os.path.basename(inputFile)

        target_file = core.os.path.join(output_destination, full_file_name)
        if input_category in core.NOFLATTEN:
            if not os.path.basename(file_path) in output_destination:
                target_file = core.os.path.join(
                    core.os.path.join(output_destination, os.path.basename(file_path)), full_file_name)
                logger.debug('Setting outputDestination to {0} to preserve folder structure'.format
                             (os.path.dirname(target_file)))
        if root == 1:
            if not found_file:
                logger.debug('Looking for {0} in: {1}'.format(input_name, inputFile))
            if any([core.sanitize_name(input_name) in core.sanitize_name(inputFile),
                    core.sanitize_name(file_name) in core.sanitize_name(input_name)]):
                found_file = True
                logger.debug('Found file {0} that matches Torrent Name {1}'.format
                             (full_file_name, input_name))
            else:
                continue

        if root == 2:
            mtime_lapse = now - datetime.datetime.fromtimestamp(os.path.getmtime(inputFile))
            ctime_lapse = now - datetime.datetime.fromtimestamp(os.path.getctime(inputFile))

            if not found_file:
                logger.debug('Looking for files with modified/created dates less than 5 minutes old.')
            if (mtime_lapse < datetime.timedelta(minutes=5)) or (ctime_lapse < datetime.timedelta(minutes=5)):
                found_file = True
                logger.debug('Found file {0} with date modified/created less than 5 minutes ago.'.format
                             (full_file_name))
            else:
                continue  # This file has not been recently moved or created, skip it

        if torrent_no_link == 0:
            try:
                core.copy_link(inputFile, target_file, core.USE_LINK)
                core.remove_read_only(target_file)
            except Exception:
                logger.error('Failed to link: {0} to {1}'.format(inputFile, target_file))

    input_name, output_destination = convert_to_ascii(input_name, output_destination)

    if extract == 1:
        logger.debug('Checking for archives to extract in directory: {0}'.format(input_directory))
        core.extract_files(input_directory, output_destination, keep_archive)

    if input_category not in core.NOFLATTEN:
        # don't flatten hp in case multi cd albums, and we need to copy this back later.
        core.flatten(output_destination)

    # Now check if video files exist in destination:
    if section_name in ['SickBeard', 'SiCKRAGE', 'NzbDrone', 'Sonarr', 'CouchPotato', 'Radarr', 'Watcher3']:
        num_videos = len(
            core.list_media_files(output_destination, media=True, audio=False, meta=False, archives=False))
        if num_videos > 0:
            logger.info('Found {0} media files in {1}'.format(num_videos, output_destination))
            status = 0
        elif extract != 1:
            logger.info('Found no media files in {0}. Sending to {1} to process'.format(output_destination, section_name))
            status = 0
        else:
            logger.warning('Found no media files in {0}'.format(output_destination))

    # Only these sections can handling failed downloads
    # so make sure everything else gets through without the check for failed
    if section_name not in ['CouchPotato', 'Radarr', 'SickBeard', 'SiCKRAGE', 'NzbDrone', 'Sonarr', 'Watcher3']:
        status = 0

    logger.info('Calling {0}:{1} to post-process:{2}'.format(section_name, usercat, input_name))

    if core.TORRENT_CHMOD_DIRECTORY:
        core.rchmod(output_destination, core.TORRENT_CHMOD_DIRECTORY)

    result = ProcessResult(
        message='',
        status_code=0,
    )
    if section_name == 'UserScript':
        result = external_script(output_destination, input_name, input_category, section)
    elif section_name in ['CouchPotato', 'Radarr', 'Watcher3']:
        result = movies.process(section_name, output_destination, input_name, status, client_agent, input_hash, input_category)
    elif section_name in ['SickBeard', 'SiCKRAGE', 'NzbDrone', 'Sonarr']:
        if input_hash:
            input_hash = input_hash.upper()
        result = tv.process(section_name, output_destination, input_name, status, client_agent, input_hash, input_category)
    elif section_name in ['HeadPhones', 'Lidarr']:
        result = music.process(section_name, output_destination, input_name, status, client_agent, input_category)
    elif section_name == 'Mylar':
        result = comics.process(section_name, output_destination, input_name, status, client_agent, input_category)
    elif section_name == 'Gamez':
        result = games.process(section_name, output_destination, input_name, status, client_agent, input_category)
    elif section_name == 'LazyLibrarian':
        result = books.process(section_name, output_destination, input_name, status, client_agent, input_category)

    plex_update(input_category)

    if result.status_code != 0:
        if not core.TORRENT_RESUME_ON_FAILURE:
            logger.error('A problem was reported in the autoProcess* script. '
                         'Torrent won\'t resume seeding (settings)')
        elif client_agent != 'manual':
            logger.error('A problem was reported in the autoProcess* script. '
                         'If torrent was paused we will resume seeding')
            core.resume_torrent(client_agent, input_hash, input_id, input_name)

    else:
        if client_agent != 'manual':
            # update download status in our DB
            core.update_download_info_status(input_name, 1)

            # remove torrent
            if core.USE_LINK == 'move-sym' and not core.DELETE_ORIGINAL == 1:
                logger.debug('Checking for sym-links to re-direct in: {0}'.format(input_directory))
                for dirpath, _, files in os.walk(input_directory):
                    for file in files:
                        logger.debug('Checking symlink: {0}'.format(os.path.join(dirpath, file)))
                        replace_links(os.path.join(dirpath, file))
            core.remove_torrent(client_agent, input_hash, input_id, input_name)

        if section_name != 'UserScript':
            # for user script, we assume this is cleaned by the script or option USER_SCRIPT_CLEAN
            # cleanup our processing folders of any misc unwanted files and empty directories
            core.clean_dir(output_destination, section_name, input_category)

    return result


def main(args):
    # Initialize the config
    core.initialize()

    # clientAgent for Torrents
    client_agent = core.TORRENT_CLIENT_AGENT

    logger.info('#########################################################')
    logger.info('## ..::[{0}]::.. ##'.format(os.path.basename(__file__)))
    logger.info('#########################################################')

    # debug command line options
    logger.debug('Options passed into TorrentToMedia: {0}'.format(args))

    # Post-Processing Result
    result = ProcessResult(
        message='',
        status_code=0,
    )

    try:
        input_directory, input_name, input_category, input_hash, input_id = core.parse_args(client_agent, args)
    except Exception:
        logger.error('There was a problem loading variables')
        return -1

    if input_directory and input_name and input_hash and input_id:
        result = process_torrent(input_directory, input_name, input_category, input_hash, input_id, client_agent)
    elif core.TORRENT_NO_MANUAL:
        logger.warning('Invalid number of arguments received from client, and no_manual set')
    else:
        # Perform Manual Post-Processing
        logger.warning('Invalid number of arguments received from client, Switching to manual run mode ...')

        for section, subsections in core.SECTIONS.items():
            for subsection in subsections:
                if not core.CFG[section][subsection].isenabled():
                    continue
                for dir_name in core.get_dirs(section, subsection, link='hard'):
                    logger.info('Starting manual run for {0}:{1} - Folder:{2}'.format
                                (section, subsection, dir_name))

                    logger.info('Checking database for download info for {0} ...'.format
                                (os.path.basename(dir_name)))
                    core.DOWNLOAD_INFO = core.get_download_info(os.path.basename(dir_name), 0)
                    if core.DOWNLOAD_INFO:
                        client_agent = text_type(core.DOWNLOAD_INFO[0]['client_agent']) or 'manual'
                        input_hash = text_type(core.DOWNLOAD_INFO[0]['input_hash']) or ''
                        input_id = text_type(core.DOWNLOAD_INFO[0]['input_id']) or ''
                        logger.info('Found download info for {0}, '
                                    'setting variables now ...'.format(os.path.basename(dir_name)))
                    else:
                        logger.info('Unable to locate download info for {0}, '
                                    'continuing to try and process this release ...'.format
                                    (os.path.basename(dir_name)))
                        client_agent = 'manual'
                        input_hash = ''
                        input_id = ''

                    if client_agent.lower() not in core.TORRENT_CLIENTS:
                        continue

                    input_name = os.path.basename(dir_name)

                    results = process_torrent(dir_name, input_name, subsection, input_hash or None, input_id or None,
                                              client_agent)
                    if results.status_code != 0:
                        logger.error('A problem was reported when trying to perform a manual run for {0}:{1}.'.format
                                     (section, subsection))
                        result = results

    if result.status_code == 0:
        logger.info('The {0} script completed successfully.'.format(args[0]))
    else:
        logger.error('A problem was reported in the {0} script.'.format(args[0]))
    del core.MYAPP
    return result.status_code


if __name__ == '__main__':
    exit(main(sys.argv))
