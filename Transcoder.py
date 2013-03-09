import sys
import os
import ConfigParser
import logging

from nzbToMediaEnv import *
from nzbToMediaSceneExceptions import process_all_exceptions

Logger = logging.getLogger()

def Transcode_file(filePath):
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    config.read(configFilename)
    
    duplicate = config.get("Transcoder", "duplicate")
    outputVideoExtension = config.get("Transcoder", "outputVideoExtension")
    outputVideoCodec = config.get("Transcoder", "outputVideoCodec")
    outputVideoFramrate = config.get("Transcoder", "outputVideoFramrate")
    outputVideoBitrate = config.get("Transcoder", "outputVideoBitrate")
    outputAudioCodec = config.get("Transcoder", "outputAudioCodec")
    outputAudioBitrate = config.get("Transcoder", "outputAudioBitrate")
    
    name, ext = os.path.splitext(file)
    newfilePath = os.path.normpath(name + outputVideoExtension)
    #ffmpeg = os.path.join(os.path.join(os.path.normpath(sys.argv[0]), ffmpeg), ffmpeg) #if not in path... got to figure out where this goes.
    command = ['ffmpeg', '-i', filePath]
    if outputVideoCodec:
        command.append('-c:v')
        command.append(outputVideoCodec)
    if outputVideoFramrate:
        command.append('-r')
        command.append(outputVideoFramerate)
    if outputVideoBitrate:
        command.append('-b:v')
        command.append(outputVideoBitrate)
    if outputAudioCodec:
        command.append('-c:a')
        command.append(outputAudioCodec)
    if outputAudioBitrate:
        command.append('-b:a')
        command.append(outputAudioBitrate)
    command.append(newfilePath)

    Logger.info("Transcoding video %s to %s", filePath, newfilePath)
    try:
        result = call(command)
    except e:
        Logger.error("Transcoding of video %s failed due to: ", filePath, str(e))
    if result == 0:
        Logger.info("Transcoding of video %s to %s succeded", filePath, newfilePath)
        if duplicate == 0: # we get rid of the original file
            os.unlink(filePath)
    else:
        Logger.error("Transcoding of video %s to %s failed", filePath, newfilePath)
    return result
    

        
    
