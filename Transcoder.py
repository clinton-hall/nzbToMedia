import sys
import os
import ConfigParser
import logging
from subprocess import call

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
    ffmpeg = os.path.normpath(config.get("Transcoder", "ffmpeg"))
    ignoreExtensions = (config.get("Transcoder", "ignoreExtensions")).split(',')
    outputVideoExtension = config.get("Transcoder", "outputVideoExtension")
    outputVideoCodec = config.get("Transcoder", "outputVideoCodec")
    outputVideoFramrate = config.get("Transcoder", "outputVideoFramrate")
    outputVideoBitrate = config.get("Transcoder", "outputVideoBitrate")
    outputAudioCodec = config.get("Transcoder", "outputAudioCodec")
    outputAudioBitrate = config.get("Transcoder", "outputAudioBitrate")
    
    name, ext = os.path.splitext(file)
    if ext in ignoreExtensions:
        Logger.info("No need to transcode video type %s", ext)
        return 0 # exit Transcoder.
    if ext == outputVideoExtension: # we need to change the name to prevent overwriting itself.
        outputVideoExtension = '-transcoded' + outputVideoExtension # adds '-transcoded.ext'
    newfilePath = os.path.normpath(name + outputVideoExtension)
    
    command = [ffmpeg, '-i', filePath]
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
        command.append('lib' + outputAudioCodec + 'lame')
    if outputAudioBitrate:
        command.append('-b:a')
        command.append(outputAudioBitrate)
    command.append(newfilePath)

    Logger.debug("Transcoding video %s to %s", filePath, newfilePath)
    result = 1 # set result to failed in case call fails.
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
    

        
    
