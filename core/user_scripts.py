import os
from subprocess import Popen

import core
from core import logger, transcoder
from core.plugins.subtitles import import_subs
from core.utils import list_media_files, remove_dir
from core.auto_process.common import (
    ProcessResult,
)


def external_script(output_destination, torrent_name, torrent_label, settings):
    final_result = 0  # start at 0.
    num_files = 0
    core.USER_SCRIPT_MEDIAEXTENSIONS = settings.get('user_script_mediaExtensions', '')
    try:
        if isinstance(core.USER_SCRIPT_MEDIAEXTENSIONS, str):
            core.USER_SCRIPT_MEDIAEXTENSIONS = core.USER_SCRIPT_MEDIAEXTENSIONS.lower().split(',')
    except Exception:
        logger.error('user_script_mediaExtensions could not be set', 'USERSCRIPT')
        core.USER_SCRIPT_MEDIAEXTENSIONS = []

    core.USER_SCRIPT = settings.get('user_script_path', '')

    if not core.USER_SCRIPT or core.USER_SCRIPT == 'None':
        # do nothing and return success. This allows the user an option to Link files only and not run a script.
        return ProcessResult(
            status_code=0,
            message='No user script defined',
        )

    core.USER_SCRIPT_PARAM = settings.get('user_script_param', '')
    try:
        if isinstance(core.USER_SCRIPT_PARAM, str):
            core.USER_SCRIPT_PARAM = core.USER_SCRIPT_PARAM.split(',')
    except Exception:
        logger.error('user_script_params could not be set', 'USERSCRIPT')
        core.USER_SCRIPT_PARAM = []

    core.USER_SCRIPT_SUCCESSCODES = settings.get('user_script_successCodes', 0)
    try:
        if isinstance(core.USER_SCRIPT_SUCCESSCODES, str):
            core.USER_SCRIPT_SUCCESSCODES = core.USER_SCRIPT_SUCCESSCODES.split(',')
    except Exception:
        logger.error('user_script_successCodes could not be set', 'USERSCRIPT')
        core.USER_SCRIPT_SUCCESSCODES = 0

    core.USER_SCRIPT_CLEAN = int(settings.get('user_script_clean', 1))
    core.USER_SCRIPT_RUNONCE = int(settings.get('user_script_runOnce', 1))

    if core.CHECK_MEDIA:
        for video in list_media_files(output_destination, media=True, audio=False, meta=False, archives=False):
            if transcoder.is_video_good(video, 0):
                import_subs(video)
            else:
                logger.info(f'Corrupt video file found {video}. Deleting.', 'USERSCRIPT')
                os.unlink(video)

    for dirpath, _, filenames in os.walk(output_destination):
        for file in filenames:

            file_path = core.os.path.join(dirpath, file)
            file_name, file_extension = os.path.splitext(file)
            logger.debug(f'Checking file {file} to see if this should be processed.', 'USERSCRIPT')

            if file_extension in core.USER_SCRIPT_MEDIAEXTENSIONS or 'all' in core.USER_SCRIPT_MEDIAEXTENSIONS:
                num_files += 1
                if core.USER_SCRIPT_RUNONCE == 1 and num_files > 1:  # we have already run once, so just continue to get number of files.
                    continue
                command = [core.USER_SCRIPT]
                for param in core.USER_SCRIPT_PARAM:
                    if param == 'FN':
                        command.append(f'{file}')
                        continue
                    elif param == 'FP':
                        command.append(f'{file_path}')
                        continue
                    elif param == 'TN':
                        command.append(f'{torrent_name}')
                        continue
                    elif param == 'TL':
                        command.append(f'{torrent_label}')
                        continue
                    elif param == 'DN':
                        if core.USER_SCRIPT_RUNONCE == 1:
                            command.append(f'{output_destination}')
                        else:
                            command.append(f'{dirpath}')
                        continue
                    else:
                        command.append(param)
                        continue
                cmd = ''
                for item in command:
                    cmd = f'{cmd} {item}'
                logger.info(f'Running script {cmd} on file {file_path}.', 'USERSCRIPT')
                try:
                    p = Popen(command)
                    res = p.wait()
                    if str(res) in core.USER_SCRIPT_SUCCESSCODES:  # Linux returns 0 for successful.
                        logger.info(f'UserScript {command[0]} was successfull')
                        result = 0
                    else:
                        logger.error(f'UserScript {command[0]} has failed with return code: {res}', 'USERSCRIPT')
                        logger.info(f'If the UserScript completed successfully you should add {res} to the user_script_successCodes', 'USERSCRIPT')
                        result = int(1)
                except Exception:
                    logger.error(f'UserScript {command[0]} has failed', 'USERSCRIPT')
                    result = int(1)
                final_result += result

    num_files_new = 0
    for _, _, filenames in os.walk(output_destination):
        for file in filenames:
            file_name, file_extension = os.path.splitext(file)

            if file_extension in core.USER_SCRIPT_MEDIAEXTENSIONS or core.USER_SCRIPT_MEDIAEXTENSIONS == 'ALL':
                num_files_new += 1

    if core.USER_SCRIPT_CLEAN == int(1) and num_files_new == 0 and final_result == 0:
        logger.info(f'All files have been processed. Cleaning outputDirectory {output_destination}')
        remove_dir(output_destination)
    elif core.USER_SCRIPT_CLEAN == int(1) and num_files_new != 0:
        logger.info(f'{num_files} files were processed, but {num_files_new} still remain. outputDirectory will not be cleaned.')
    return ProcessResult(
        status_code=final_result,
        message='User Script Completed',
    )
