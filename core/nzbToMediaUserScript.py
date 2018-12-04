# coding=utf-8
import os
import core
from subprocess import Popen
from core.transcoder import transcoder
from core.nzbToMediaUtil import import_subs, listMediaFiles, rmDir
from core import logger


def external_script(outputDestination, torrentName, torrentLabel, settings):
    final_result = 0  # start at 0.
    num_files = 0
    try:
        core.USER_SCRIPT_MEDIAEXTENSIONS = settings["user_script_mediaExtensions"].lower()
        if isinstance(core.USER_SCRIPT_MEDIAEXTENSIONS, str):
            core.USER_SCRIPT_MEDIAEXTENSIONS = core.USER_SCRIPT_MEDIAEXTENSIONS.split(',')
    except:
        core.USER_SCRIPT_MEDIAEXTENSIONS = []

    core.USER_SCRIPT = settings.get("user_script_path")

    if not core.USER_SCRIPT or core.USER_SCRIPT == "None":  # do nothing and return success.
        return [0, ""]
    try:
        core.USER_SCRIPT_PARAM = settings["user_script_param"]
        if isinstance(core.USER_SCRIPT_PARAM, str):
            core.USER_SCRIPT_PARAM = core.USER_SCRIPT_PARAM.split(',')
    except:
        core.USER_SCRIPT_PARAM = []
    try:
        core.USER_SCRIPT_SUCCESSCODES = settings["user_script_successCodes"]
        if isinstance(core.USER_SCRIPT_SUCCESSCODES, str):
            core.USER_SCRIPT_SUCCESSCODES = core.USER_SCRIPT_SUCCESSCODES.split(',')
    except:
        core.USER_SCRIPT_SUCCESSCODES = 0

    core.USER_SCRIPT_CLEAN = int(settings.get("user_script_clean", 1))
    core.USER_SCRIPT_RUNONCE = int(settings.get("user_script_runOnce", 1))

    if core.CHECK_MEDIA:
        for video in listMediaFiles(outputDestination, media=True, audio=False, meta=False, archives=False):
            if transcoder.isVideoGood(video, 0):
                import_subs(video)
            else:
                logger.info("Corrupt video file found {0}. Deleting.".format(video), "USERSCRIPT")
                os.unlink(video)

    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:

            filePath = core.os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in core.USER_SCRIPT_MEDIAEXTENSIONS or "all" in core.USER_SCRIPT_MEDIAEXTENSIONS:
                num_files += 1
                if core.USER_SCRIPT_RUNONCE == 1 and num_files > 1:  # we have already run once, so just continue to get number of files.
                    continue
                command = [core.USER_SCRIPT]
                for param in core.USER_SCRIPT_PARAM:
                    if param == "FN":
                        command.append('{0}'.format(file))
                        continue
                    elif param == "FP":
                        command.append('{0}'.format(filePath))
                        continue
                    elif param == "TN":
                        command.append('{0}'.format(torrentName))
                        continue
                    elif param == "TL":
                        command.append('{0}'.format(torrentLabel))
                        continue
                    elif param == "DN":
                        if core.USER_SCRIPT_RUNONCE == 1:
                            command.append('{0}'.format(outputDestination))
                        else:
                            command.append('{0}'.format(dirpath))
                        continue
                    else:
                        command.append(param)
                        continue
                cmd = ""
                for item in command:
                    cmd = "{cmd} {item}".format(cmd=cmd, item=item)
                logger.info("Running script {cmd} on file {path}.".format(cmd=cmd, path=filePath), "USERSCRIPT")
                try:
                    p = Popen(command)
                    res = p.wait()
                    if str(res) in core.USER_SCRIPT_SUCCESSCODES:  # Linux returns 0 for successful.
                        logger.info("UserScript {0} was successfull".format(command[0]))
                        result = 0
                    else:
                        logger.error("UserScript {0} has failed with return code: {1}".format(command[0], res), "USERSCRIPT")
                        logger.info(
                            "If the UserScript completed successfully you should add {0} to the user_script_successCodes".format(
                                res), "USERSCRIPT")
                        result = int(1)
                except:
                    logger.error("UserScript {0} has failed".format(command[0]), "USERSCRIPT")
                    result = int(1)
                final_result += result

    num_files_new = 0
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in core.USER_SCRIPT_MEDIAEXTENSIONS or core.USER_SCRIPT_MEDIAEXTENSIONS == "ALL":
                num_files_new += 1

    if core.USER_SCRIPT_CLEAN == int(1) and num_files_new == 0 and final_result == 0:
        logger.info("All files have been processed. Cleaning outputDirectory {0}".format(outputDestination))
        rmDir(outputDestination)
    elif core.USER_SCRIPT_CLEAN == int(1) and num_files_new != 0:
        logger.info("{0} files were processed, but {1} still remain. outputDirectory will not be cleaned.".format(
            num_files, num_files_new))
    return [final_result, '']
