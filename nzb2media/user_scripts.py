from __future__ import annotations

import logging
import os
from subprocess import Popen

import nzb2media
from nzb2media import transcoder
from nzb2media.auto_process.common import ProcessResult
from nzb2media.subtitles import import_subs
from nzb2media.utils.files import list_media_files
from nzb2media.utils.paths import remove_dir

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

MEDIA_EXTENSIONS = None
SCRIPT = None
PARAMETERS = None
SUCCESS_CODES = None
CLEAN = None
DELAY = None
RUN_ONCE = None


def external_script(output_destination, torrent_name, torrent_label, settings):
    global MEDIA_EXTENSIONS
    global SCRIPT
    global PARAMETERS
    global SUCCESS_CODES
    global CLEAN
    global RUN_ONCE
    global DELAY

    final_result = 0  # start at 0.
    num_files = 0
    MEDIA_EXTENSIONS = settings.get('user_script_mediaExtensions', '')
    try:
        if isinstance(MEDIA_EXTENSIONS, str):
            MEDIA_EXTENSIONS = MEDIA_EXTENSIONS.lower().split(',')
    except Exception:
        log.error('user_script_mediaExtensions could not be set')
        MEDIA_EXTENSIONS = []
    SCRIPT = settings.get('user_script_path', '')
    if not SCRIPT or SCRIPT == 'None':
        # do nothing and return success. This allows the user an option to Link files only and not run a script.
        return ProcessResult(status_code=0, message='No user script defined')
    PARAMETERS = settings.get('user_script_param', '')
    try:
        if isinstance(PARAMETERS, str):
            PARAMETERS = PARAMETERS.split(',')
    except Exception:
        log.error('user_script_params could not be set')
        PARAMETERS = []
    SUCCESS_CODES = settings.get('user_script_successCodes', 0)
    try:
        if isinstance(SUCCESS_CODES, str):
            SUCCESS_CODES = SUCCESS_CODES.split(',')
    except Exception:
        log.error('user_script_successCodes could not be set')
        SUCCESS_CODES = 0
    CLEAN = int(settings.get('user_script_clean', 1))
    RUN_ONCE = int(settings.get('user_script_runOnce', 1))
    if nzb2media.CHECK_MEDIA:
        for video in list_media_files(output_destination, audio=False, meta=False, archives=False):
            if transcoder.is_video_good(video, 0):
                import_subs(video)
            else:
                log.info(f'Corrupt video file found {video}. Deleting.')
                os.unlink(video)
    for dirpath, _, filenames in os.walk(output_destination):
        for file in filenames:
            file_path = nzb2media.os.path.join(dirpath, file)
            file_name, file_extension = os.path.splitext(file)
            log.debug(f'Checking file {file} to see if this should be processed.')
            if file_extension in MEDIA_EXTENSIONS or 'all' in MEDIA_EXTENSIONS:
                num_files += 1
                if RUN_ONCE == 1 and num_files > 1:  # we have already run once, so just continue to get number of files.
                    continue
                command = [SCRIPT]
                for param in PARAMETERS:
                    if param == 'FN':
                        command.append(f'{file}')
                        continue
                    if param == 'FP':
                        command.append(f'{file_path}')
                        continue
                    if param == 'TN':
                        command.append(f'{torrent_name}')
                        continue
                    if param == 'TL':
                        command.append(f'{torrent_label}')
                        continue
                    if param == 'DN':
                        if RUN_ONCE == 1:
                            command.append(f'{output_destination}')
                        else:
                            command.append(f'{dirpath}')
                        continue
                    command.append(param)
                cmd = ''
                for item in command:
                    cmd = f'{cmd} {item}'
                log.info(f'Running script {cmd} on file {file_path}.')
                try:
                    with Popen(command) as proc:
                        res = proc.wait()
                except Exception:
                    log.error(f'UserScript {command[0]} has failed')
                    result = 1
                else:
                    if str(res) in SUCCESS_CODES:
                        # Linux returns 0 for successful.
                        log.info(f'UserScript {command[0]} was successfull')
                        result = 0
                    else:
                        log.error(f'UserScript {command[0]} has failed with return code: {res}')
                        log.info(f'If the UserScript completed successfully you should add {res} to the user_script_successCodes')
                        result = 1
                final_result += result
    num_files_new = 0
    for _, _, filenames in os.walk(output_destination):
        for file in filenames:
            file_name, file_extension = os.path.splitext(file)
            if file_extension in MEDIA_EXTENSIONS or MEDIA_EXTENSIONS == 'ALL':
                num_files_new += 1
    if CLEAN == 1 and not num_files_new and not final_result:
        log.info(f'All files have been processed. Cleaning outputDirectory {output_destination}')
        remove_dir(output_destination)
    elif CLEAN == 1 and num_files_new:
        log.info(f'{num_files} files were processed, but {num_files_new} still remain. outputDirectory will not be cleaned.')
    return ProcessResult(status_code=final_result, message='User Script Completed')
