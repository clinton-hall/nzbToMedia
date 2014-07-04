import os
import nzbtomedia
from subprocess import Popen
from nzbtomedia.transcoder import transcoder
from nzbtomedia.nzbToMediaUtil import import_subs, listMediaFiles
from nzbtomedia import logger

def external_script(outputDestination, torrentName, torrentLabel, settings):
    if nzbtomedia.USER_SCRIPT is None or nzbtomedia.USER_SCRIPT == "None":  # do nothing and return success.
        return 0
    final_result = 0  # start at 0.
    num_files = 0
    try:
        nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS = settings["user_script_mediaExtensions"]
        if isinstance(nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS, str): nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS = nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS.split(',')
    except:
        nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS = []
    try:
        nzbtomedia.USER_SCRIPT = settings["user_script_path"]
    except:
        nzbtomedia.USER_SCRIPT = None
    try:
        nzbtomedia.USER_SCRIPT_PARAM = settings["user_script_param"]
        if isinstance(nzbtomedia.USER_SCRIPT_PARAM, str): nzbtomedia.USER_SCRIPT_PARAM = nzbtomedia.USER_SCRIPT_PARAM.split(',')
    except:
        nzbtomedia.USER_SCRIPT_PARAM = []
    try:
        nzbtomedia.USER_SCRIPT_SUCCESSCODES = settings["user_script_successCodes"]
        if isinstance(nzbtomedia.USER_SCRIPT_SUCCESSCODES, str): nzbtomedia.USER_SCRIPT_SUCCESSCODES = nzbtomedia.USER_SCRIPT_SUCCESSCODES.split(',')
    except:
        nzbtomedia.USER_SCRIPT_SUCCESSCODES = 0
    try:
        nzbtomedia.USER_SCRIPT_CLEAN = int(settings["user_script_clean"])
    except:
        nzbtomedia.USER_SCRIPT_CLEAN = 1
    try:
        nzbtomedia.USER_SCRIPT_RUNONCE = int(settings["user_script_runOnce"])
    except:
        nzbtomedia.USER_SCRIPT_RUNONCE = 1

    if nzbtomedia.CHECK_MEDIA:
        for video in listMediaFiles(outputDestination, media=True, audio=False, meta=False, archives=False):
            if transcoder.isVideoGood(video, 0):
                import_subs(video)
            else:
                logger.info("Corrupt video file found %s. Deleting." % (video), "USERSCRIPT")
                os.unlink(video)

    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:

            filePath = nzbtomedia.os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS or "ALL" in nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS:
                num_files = num_files + 1
                if nzbtomedia.USER_SCRIPT_RUNONCE == 1 and num_files > 1:  # we have already run once, so just continue to get number of files.
                    continue
                command = [nzbtomedia.USER_SCRIPT]
                for param in nzbtomedia.USER_SCRIPT_PARAM:
                    if param == "FN":
                        command.append(file)
                        continue
                    elif param == "FP":
                        command.append(filePath)
                        continue
                    elif param == "TN":
                        command.append(torrentName)
                        continue
                    elif param == "TL":
                        command.append(torrentLabel)
                        continue
                    elif param == "DN":
                        if nzbtomedia.USER_SCRIPT_RUNONCE == 1:
                            command.append(outputDestination)
                        else:
                            command.append(dirpath)
                        continue
                    else:
                        command.append(param)
                        continue
                cmd = ""
                for item in command:
                    cmd = cmd + " " + item
                logger.info("Running script %s on file %s." % (cmd, filePath), "USERSCRIPT")
                try:
                    p = Popen(command)
                    res = p.wait()
                    if str(res) in nzbtomedia.USER_SCRIPT_SUCCESSCODES:  # Linux returns 0 for successful.
                        logger.info("UserScript %s was successfull" % (command[0]))
                        result = 0
                    else:
                        logger.error("UserScript %s has failed with return code: %s" % (command[0], res), "USERSCRIPT")
                        logger.info(
                            "If the UserScript completed successfully you should add %s to the user_script_successCodes" % (
                                res), "USERSCRIPT")
                        result = int(1)
                except:
                    logger.error("UserScript %s has failed" % (command[0]), "USERSCRIPT")
                    result = int(1)
                final_result = final_result + result

    num_files_new = 0
    for dirpath, dirnames, filenames in os.walk(outputDestination):
        for file in filenames:
            filePath = nzbtomedia.os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS or nzbtomedia.USER_SCRIPT_MEDIAEXTENSIONS == "ALL":
                num_files_new = num_files_new + 1

    if nzbtomedia.USER_SCRIPT_CLEAN == int(1) and num_files_new == 0 and final_result == 0:
        logger.info("All files have been processed. Cleaning outputDirectory %s" % (outputDestination))
        shutil.rmtree(outputDestination)
    elif nzbtomedia.USER_SCRIPT_CLEAN == int(1) and num_files_new != 0:
        logger.info("%s files were processed, but %s still remain. outputDirectory will not be cleaned." % (
            num_files, num_files_new))
    return final_result
