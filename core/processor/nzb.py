import datetime

import core
from core import logger, main_db
from core.auto_process import comics, games, movies, music, tv, books
from core.auto_process.common import ProcessResult
from core.plugins.downloaders.nzb.utils import get_nzoid
from core.plugins.plex import plex_update
from core.user_scripts import external_script
from core.utils import (
    char_replace,
    clean_dir,
    convert_to_ascii,
    extract_files,
    update_download_info_status,
)

try:
    text_type = unicode
except NameError:
    text_type = str


def process(input_directory, input_name=None, status=0, client_agent='manual', download_id=None, input_category=None, failure_link=None):
    if core.SAFE_MODE and input_directory == core.NZB_DEFAULT_DIRECTORY:
        logger.error(
            'The input directory:[{0}] is the Default Download Directory. Please configure category directories to prevent processing of other media.'.format(
                input_directory))
        return ProcessResult(
            message='',
            status_code=-1,
        )

    if not download_id and client_agent == 'sabnzbd':
        download_id = get_nzoid(input_name)

    if client_agent != 'manual' and not core.DOWNLOAD_INFO:
        logger.debug('Adding NZB download info for directory {0} to database'.format(input_directory))

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
            'input_hash': text_type(download_id),
            'input_id': text_type(download_id),
            'client_agent': text_type(client_agent),
            'status': 0,
            'last_update': datetime.date.today().toordinal(),
        }
        my_db.upsert('downloads', new_value_dict, control_value_dict)

    # auto-detect section
    if input_category is None:
        input_category = 'UNCAT'
    usercat = input_category
    section = core.CFG.findsection(input_category).isenabled()
    if section is None:
        section = core.CFG.findsection('ALL').isenabled()
        if section is None:
            logger.error(
                'Category:[{0}] is not defined or is not enabled. Please rename it or ensure it is enabled for the appropriate section in your autoProcessMedia.cfg and try again.'.format(
                    input_category))
            return ProcessResult(
                message='',
                status_code=-1,
            )
        else:
            usercat = 'ALL'

    if len(section) > 1:
        logger.error(
            'Category:[{0}] is not unique, {1} are using it. Please rename it or disable all other sections using the same category name in your autoProcessMedia.cfg and try again.'.format(
                input_category, section.keys()))
        return ProcessResult(
            message='',
            status_code=-1,
        )

    if section:
        section_name = section.keys()[0]
        logger.info('Auto-detected SECTION:{0}'.format(section_name))
    else:
        logger.error('Unable to locate a section with subsection:{0} enabled in your autoProcessMedia.cfg, exiting!'.format(
            input_category))
        return ProcessResult(
            status_code=-1,
            message='',
        )

    cfg = dict(core.CFG[section_name][usercat])

    extract = int(cfg.get('extract', 0))

    try:
        if int(cfg.get('remote_path')) and not core.REMOTE_PATHS:
            logger.error('Remote Path is enabled for {0}:{1} but no Network mount points are defined. Please check your autoProcessMedia.cfg, exiting!'.format(
                section_name, input_category))
            return ProcessResult(
                status_code=-1,
                message='',
            )
    except Exception:
        logger.error('Remote Path {0} is not valid for {1}:{2} Please set this to either 0 to disable or 1 to enable!'.format(
            cfg.get('remote_path'), section_name, input_category))

    input_name, input_directory = convert_to_ascii(input_name, input_directory)

    if extract == 1 and not (status > 0 and core.NOEXTRACTFAILED):
        logger.debug('Checking for archives to extract in directory: {0}'.format(input_directory))
        extract_files(input_directory)

    logger.info('Calling {0}:{1} to post-process:{2}'.format(section_name, input_category, input_name))

    if section_name in ['CouchPotato', 'Radarr', 'Watcher3']:
        result = movies.process(section_name, input_directory, input_name, status, client_agent, download_id, input_category, failure_link)
    elif section_name in ['SickBeard', 'SiCKRAGE', 'NzbDrone', 'Sonarr']:
        result = tv.process(section_name, input_directory, input_name, status, client_agent, download_id, input_category, failure_link)
    elif section_name in ['HeadPhones', 'Lidarr']:
        result = music.process(section_name, input_directory, input_name, status, client_agent, input_category)
    elif section_name == 'Mylar':
        result = comics.process(section_name, input_directory, input_name, status, client_agent, input_category)
    elif section_name == 'Gamez':
        result = games.process(section_name, input_directory, input_name, status, client_agent, input_category)
    elif section_name == 'LazyLibrarian':
        result = books.process(section_name, input_directory, input_name, status, client_agent, input_category)
    elif section_name == 'UserScript':
        result = external_script(input_directory, input_name, input_category, section[usercat])
    else:
        result = ProcessResult(
            message='',
            status_code=-1,
        )

    plex_update(input_category)

    if result.status_code == 0:
        if client_agent != 'manual':
            # update download status in our DB
            update_download_info_status(input_name, 1)
        if section_name not in ['UserScript', 'NzbDrone', 'Sonarr', 'Radarr', 'Lidarr']:
            # cleanup our processing folders of any misc unwanted files and empty directories
            clean_dir(input_directory, section_name, input_category)

    return result
