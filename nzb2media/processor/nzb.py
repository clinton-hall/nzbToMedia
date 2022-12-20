from __future__ import annotations

import datetime
import logging

import nzb2media
import nzb2media.nzb
from nzb2media import main_db
from nzb2media.auto_process import books
from nzb2media.auto_process import comics
from nzb2media.auto_process import games
from nzb2media.auto_process import movies
from nzb2media.auto_process import music
from nzb2media.auto_process import tv
from nzb2media.auto_process.common import ProcessResult
from nzb2media.nzb import get_nzoid
from nzb2media.plex import plex_update
from nzb2media.user_scripts import external_script
from nzb2media.utils.common import clean_dir
from nzb2media.utils.download_info import update_download_info_status
from nzb2media.utils.encoding import char_replace
from nzb2media.utils.encoding import convert_to_ascii
from nzb2media.utils.files import extract_files

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def process(*, input_directory, input_name=None, status=0, client_agent='manual', download_id=None, input_category=None, failure_link=None):
    if nzb2media.SAFE_MODE and input_directory == nzb2media.nzb.DEFAULT_DIRECTORY:
        log.error(f'The input directory:[{input_directory}] is the Default Download Directory. Please configure category directories to prevent processing of other media.')
        return ProcessResult(message='', status_code=-1)
    if not download_id and client_agent == 'sabnzbd':
        download_id = get_nzoid(input_name)
    if client_agent != 'manual' and not nzb2media.DOWNLOAD_INFO:
        log.debug(f'Adding NZB download info for directory {input_directory} to database')
        my_db = main_db.DBConnection()
        input_directory1 = input_directory
        input_name1 = input_name
        try:
            encoded, input_directory1 = char_replace(input_directory)
            encoded, input_name1 = char_replace(input_name)
        except Exception:
            pass
        control_value_dict = {'input_directory': input_directory1}
        new_value_dict = {'input_name': input_name1, 'input_hash': download_id, 'input_id': download_id, 'client_agent': client_agent, 'status': 0, 'last_update': datetime.date.today().toordinal()}
        my_db.upsert('downloads', new_value_dict, control_value_dict)
    # auto-detect SECTION
    if input_category is None:
        input_category = 'UNCAT'
    usercat = input_category
    section = nzb2media.CFG.findsection(input_category).isenabled()
    if section is None:
        section = nzb2media.CFG.findsection('ALL').isenabled()
        if section is None:
            log.error(f'Category:[{input_category}] is not defined or is not enabled. Please rename it or ensure it is enabled for the appropriate section in your autoProcessMedia.cfg and try again.')
            return ProcessResult(message='', status_code=-1)
        usercat = 'ALL'
    if len(section) > 1:
        log.error(f'Category:[{input_category}] is not unique, {section.keys()} are using it. Please rename it or disable all other sections using the same category name in your autoProcessMedia.cfg and try again.')
        return ProcessResult(message='', status_code=-1)
    if section:
        section_name = section.keys()[0]
        log.info(f'Auto-detected SECTION:{section_name}')
    else:
        log.error(f'Unable to locate a section with subsection:{input_category} enabled in your autoProcessMedia.cfg, exiting!')
        return ProcessResult(status_code=-1, message='')
    cfg = dict(nzb2media.CFG[section_name][usercat])
    extract = int(cfg.get('extract', 0))
    try:
        if int(cfg.get('remote_path')) and not nzb2media.REMOTE_PATHS:
            log.error(f'Remote Path is enabled for {section_name}:{input_category} but no Network mount points are defined. Please check your autoProcessMedia.cfg, exiting!')
            return ProcessResult(status_code=-1, message='')
    except Exception:
        remote_path = cfg.get('remote_path')
        log.error(f'Remote Path {remote_path} is not valid for {section_name}:{input_category} Please set this to either 0 to disable or 1 to enable!')
    input_name, input_directory = convert_to_ascii(input_name, input_directory)
    if extract == 1 and not (status > 0 and nzb2media.NOEXTRACTFAILED):
        log.debug(f'Checking for archives to extract in directory: {input_directory}')
        extract_files(input_directory)
    log.info(f'Calling {section_name}:{input_category} to post-process:{input_name}')
    if section_name == 'UserScript':
        result = external_script(input_directory, input_name, input_category, section[usercat])
    else:
        process_map = {'CouchPotato': movies.process, 'Radarr': movies.process, 'Watcher3': movies.process, 'SickBeard': tv.process, 'SiCKRAGE': tv.process, 'NzbDrone': tv.process, 'Sonarr': tv.process, 'LazyLibrarian': books.process, 'HeadPhones': music.process, 'Lidarr': music.process, 'Mylar': comics.process, 'Gamez': games.process}
        processor = process_map[section_name]
        result = processor(section=section_name, dir_name=input_directory, input_name=input_name, status=status, client_agent=client_agent, download_id=download_id, input_category=input_category, failure_link=failure_link)
    plex_update(input_category)
    if not result.status_code:
        if client_agent != 'manual':
            # update download status in our DB
            update_download_info_status(input_name, 1)
        if section_name not in ['UserScript', 'NzbDrone', 'Sonarr', 'Radarr', 'Lidarr']:
            # cleanup our processing folders of any misc unwanted files and
            # empty directories
            clean_dir(input_directory, section_name, input_category)
    return result
