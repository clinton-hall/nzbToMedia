#!/usr/bin/env python2
# coding=utf-8

from __future__ import print_function

import cleanup
cleanup.clean('core', 'libs')

import datetime
import os
import sys

import core
from core import logger, main_db
from core.auto_process import Comic, Game, Movie, Music, TV
from core.user_scripts import external_script
from core.utils import char_replace, clean_dir, convert_to_ascii, extract_files, get_dirs, get_download_info, get_nzoid, plex_update, update_download_info_status

try:
    text_type = unicode
except NameError:
    text_type = str


# post-processing
def process(input_directory, input_name=None, status=0, client_agent='manual', download_id=None, input_category=None, failure_link=None):
    if core.SAFE_MODE and input_directory == core.NZB_DEFAULTDIR:
        logger.error(
            'The input directory:[{0}] is the Default Download Directory. Please configure category directories to prevent processing of other media.'.format(
                input_directory))
        return [-1, ""]

    if not download_id and client_agent == 'sabnzbd':
        download_id = get_nzoid(input_name)

    if client_agent != 'manual' and not core.DOWNLOADINFO:
        logger.debug('Adding NZB download info for directory {0} to database'.format(input_directory))

        my_db = main_db.DBConnection()

        input_directory1 = input_directory
        input_name1 = input_name

        try:
            encoded, input_directory1 = char_replace(input_directory)
            encoded, input_name1 = char_replace(input_name)
        except Exception:
            pass

        control_value_dict = {"input_directory": text_type(input_directory1)}
        new_value_dict = {
            "input_name": text_type(input_name1),
            "input_hash": text_type(download_id),
            "input_id": text_type(download_id),
            "client_agent": text_type(client_agent),
            "status": 0,
            "last_update": datetime.date.today().toordinal(),
        }
        my_db.upsert("downloads", new_value_dict, control_value_dict)

    # auto-detect section
    if input_category is None:
        input_category = 'UNCAT'
    usercat = input_category
    section = core.CFG.findsection(input_category).isenabled()
    if section is None:
        section = core.CFG.findsection("ALL").isenabled()
        if section is None:
            logger.error(
                'Category:[{0}] is not defined or is not enabled. Please rename it or ensure it is enabled for the appropriate section in your autoProcessMedia.cfg and try again.'.format(
                    input_category))
            return [-1, ""]
        else:
            usercat = "ALL"

    if len(section) > 1:
        logger.error(
            'Category:[{0}] is not unique, {1} are using it. Please rename it or disable all other sections using the same category name in your autoProcessMedia.cfg and try again.'.format(
                input_category, section.keys()))
        return [-1, ""]

    if section:
        section_name = section.keys()[0]
        logger.info('Auto-detected SECTION:{0}'.format(section_name))
    else:
        logger.error("Unable to locate a section with subsection:{0} enabled in your autoProcessMedia.cfg, exiting!".format(
            input_category))
        return [-1, ""]

    cfg = dict(core.CFG[section_name][usercat])

    extract = int(cfg.get("extract", 0))

    try:
        if int(cfg.get("remote_path")) and not core.REMOTEPATHS:
            logger.error('Remote Path is enabled for {0}:{1} but no Network mount points are defined. Please check your autoProcessMedia.cfg, exiting!'.format(
                section_name, input_category))
            return [-1, ""]
    except Exception:
        logger.error('Remote Path {0} is not valid for {1}:{2} Please set this to either 0 to disable or 1 to enable!'.format(
            core.get("remote_path"), section_name, input_category))

    input_name, input_directory = convert_to_ascii(input_name, input_directory)

    if extract == 1:
        logger.debug('Checking for archives to extract in directory: {0}'.format(input_directory))
        extract_files(input_directory)

    logger.info("Calling {0}:{1} to post-process:{2}".format(section_name, input_category, input_name))

    if section_name in ["CouchPotato", "Radarr"]:
        result = Movie().process(section_name, input_directory, input_name, status, client_agent, download_id,
                                 input_category, failure_link)
    elif section_name in ["SickBeard", "NzbDrone", "Sonarr"]:
        result = TV().process(section_name, input_directory, input_name, status, client_agent,
                              download_id, input_category, failure_link)
    elif section_name in ["HeadPhones", "Lidarr"]:
        result = Music().process(section_name, input_directory, input_name, status, client_agent, input_category)
    elif section_name == "Mylar":
        result = Comic().process(section_name, input_directory, input_name, status, client_agent,
                                 input_category)
    elif section_name == "Gamez":
        result = Game().process(section_name, input_directory, input_name, status, client_agent, input_category)
    elif section_name == 'UserScript':
        result = external_script(input_directory, input_name, input_category, section[usercat])
    else:
        result = [-1, ""]

    plex_update(input_category)

    if result[0] == 0:
        if client_agent != 'manual':
            # update download status in our DB
            update_download_info_status(input_name, 1)
        if section_name not in ['UserScript', 'NzbDrone', 'Sonarr', 'Radarr', 'Lidarr']:
            # cleanup our processing folders of any misc unwanted files and empty directories
            clean_dir(input_directory, section_name, input_category)

    return result


def main(args, section=None):
    # Initialize the config
    core.initialize(section)

    logger.info("#########################################################")
    logger.info("## ..::[{0}]::.. ##".format(os.path.basename(__file__)))
    logger.info("#########################################################")

    # debug command line options
    logger.debug("Options passed into nzbToMedia: {0}".format(args))

    # Post-Processing Result
    result = [0, ""]
    status = 0

    # NZBGet
    if 'NZBOP_SCRIPTDIR' in os.environ:
        # Check if the script is called from nzbget 11.0 or later
        if os.environ['NZBOP_VERSION'][0:5] < '11.0':
            logger.error("NZBGet Version {0} is not supported. Please update NZBGet.".format(os.environ['NZBOP_VERSION']))
            sys.exit(core.NZBGET_POSTPROCESS_ERROR)

        logger.info("Script triggered from NZBGet Version {0}.".format(os.environ['NZBOP_VERSION']))

        # Check if the script is called from nzbget 13.0 or later
        if 'NZBPP_TOTALSTATUS' in os.environ:
            if not os.environ['NZBPP_TOTALSTATUS'] == 'SUCCESS':
                logger.info("Download failed with status {0}.".format(os.environ['NZBPP_STATUS']))
                status = 1

        else:
            # Check par status
            if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
                logger.warning("Par-repair failed, setting status \"failed\"")
                status = 1

            # Check unpack status
            if os.environ['NZBPP_UNPACKSTATUS'] == '1':
                logger.warning("Unpack failed, setting status \"failed\"")
                status = 1

            if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
                # Unpack was skipped due to nzb-file properties or due to errors during par-check

                if os.environ['NZBPP_HEALTH'] < 1000:
                    logger.warning(
                        "Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"")
                    logger.info("Please check your Par-check/repair settings for future downloads.")
                    status = 1

                else:
                    logger.info(
                        "Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful")
                    logger.info("Please check your Par-check/repair settings for future downloads.")

        # Check for download_id to pass to CouchPotato
        download_id = ""
        failure_link = None
        if 'NZBPR_COUCHPOTATO' in os.environ:
            download_id = os.environ['NZBPR_COUCHPOTATO']
        elif 'NZBPR_DRONE' in os.environ:
            download_id = os.environ['NZBPR_DRONE']
        elif 'NZBPR_SONARR' in os.environ:
            download_id = os.environ['NZBPR_SONARR']
        elif 'NZBPR_RADARR' in os.environ:
            download_id = os.environ['NZBPR_RADARR']
        elif 'NZBPR_LIDARR' in os.environ:
            download_id = os.environ['NZBPR_LIDARR']
        if 'NZBPR__DNZB_FAILURE' in os.environ:
            failure_link = os.environ['NZBPR__DNZB_FAILURE']

        # All checks done, now launching the script.
        client_agent = 'nzbget'
        result = process(os.environ['NZBPP_DIRECTORY'], input_name=os.environ['NZBPP_NZBNAME'], status=status,
                         client_agent=client_agent, download_id=download_id, input_category=os.environ['NZBPP_CATEGORY'],
                         failure_link=failure_link)
    # SABnzbd Pre 0.7.17
    elif len(args) == core.SABNZB_NO_OF_ARGUMENTS:
        # SABnzbd argv:
        # 1 The final directory of the job (full path)
        # 2 The original name of the NZB file
        # 3 Clean version of the job name (no path info and ".nzb" removed)
        # 4 Indexer's report number (if supported)
        # 5 User-defined category
        # 6 Group that the NZB was posted in e.g. alt.binaries.x
        # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
        client_agent = 'sabnzbd'
        logger.info("Script triggered from SABnzbd")
        result = process(args[1], input_name=args[2], status=args[7], input_category=args[5], client_agent=client_agent,
                         download_id='')
    # SABnzbd 0.7.17+
    elif len(args) >= core.SABNZB_0717_NO_OF_ARGUMENTS:
        # SABnzbd argv:
        # 1 The final directory of the job (full path)
        # 2 The original name of the NZB file
        # 3 Clean version of the job name (no path info and ".nzb" removed)
        # 4 Indexer's report number (if supported)
        # 5 User-defined category
        # 6 Group that the NZB was posted in e.g. alt.binaries.x
        # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
        # 8 Failure URL
        client_agent = 'sabnzbd'
        logger.info("Script triggered from SABnzbd 0.7.17+")
        result = process(args[1], input_name=args[2], status=args[7], input_category=args[5], client_agent=client_agent,
                         download_id='', failure_link=''.join(args[8:]))
    # Generic program
    elif len(args) > 5 and args[5] == 'generic':
        logger.info("Script triggered from generic program")
        result = process(args[1], input_name=args[2], input_category=args[3], download_id=args[4])
    else:
        # Perform Manual Post-Processing
        logger.warning("Invalid number of arguments received from client, Switching to manual run mode ...")

        for section, subsections in core.SECTIONS.items():
            for subsection in subsections:
                if not core.CFG[section][subsection].isenabled():
                    continue
                for dir_name in get_dirs(section, subsection, link='move'):
                    logger.info("Starting manual run for {0}:{1} - Folder: {2}".format(section, subsection, dir_name))
                    logger.info("Checking database for download info for {0} ...".format(os.path.basename(dir_name)))

                    core.DOWNLOADINFO = get_download_info(os.path.basename(dir_name), 0)
                    if core.DOWNLOADINFO:
                        logger.info("Found download info for {0}, "
                                    "setting variables now ...".format
                                    (os.path.basename(dir_name)))
                        client_agent = text_type(core.DOWNLOADINFO[0].get('client_agent', 'manual'))
                        download_id = text_type(core.DOWNLOADINFO[0].get('input_id', ''))
                    else:
                        logger.info('Unable to locate download info for {0}, '
                                    'continuing to try and process this release ...'.format
                                    (os.path.basename(dir_name)))
                        client_agent = 'manual'
                        download_id = ''

                    if client_agent and client_agent.lower() not in core.NZB_CLIENTS:
                        continue

                    try:
                        dir_name = dir_name.encode(core.SYS_ENCODING)
                    except UnicodeError:
                        pass
                    input_name = os.path.basename(dir_name)
                    try:
                        input_name = input_name.encode(core.SYS_ENCODING)
                    except UnicodeError:
                        pass

                    results = process(dir_name, input_name, 0, client_agent=client_agent,
                                      download_id=download_id or None, input_category=subsection)
                    if results[0] != 0:
                        logger.error("A problem was reported when trying to perform a manual run for {0}:{1}.".format
                                     (section, subsection))
                        result = results

    if result[0] == 0:
        logger.info("The {0} script completed successfully.".format(args[0]))
        if result[1]:
            print(result[1] + "!")
        if 'NZBOP_SCRIPTDIR' in os.environ:  # return code for nzbget v11
            del core.MYAPP
            return core.NZBGET_POSTPROCESS_SUCCESS
    else:
        logger.error("A problem was reported in the {0} script.".format(args[0]))
        if result[1]:
            print(result[1] + "!")
        if 'NZBOP_SCRIPTDIR' in os.environ:  # return code for nzbget v11
            del core.MYAPP
            return core.NZBGET_POSTPROCESS_ERROR
    del core.MYAPP
    return result[0]


if __name__ == '__main__':
    exit(main(sys.argv))
