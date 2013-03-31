import sys
import os
import ConfigParser
import logging
from subprocess import call

Logger = logging.getLogger()

def Transcode_directory(dirName):
    
    if os.name == 'nt':
        ffmpeg = os.path.join(os.path.dirname(sys.argv[0]), 'ffmpeg\\bin\\ffmpeg.exe') # note, will need to package in this dir.
        if not os.path.isfile(ffmpeg): # problem
            Logger.error("ffmpeg not found. ffmpeg needs to be located at: %s", ffmpeg) 
            Logger.info("Cannot transcode files in folder %s", dirName)
            return 1 # failure
    else:
        if call(['which', 'ffmpeg']) != 0:
            res = call([os.path.join(os.path.dirname(sys.argv[0]),'getffmpeg.sh')])
            if res or call(['which', 'ffmpeg']): # did not install or ffmpeg still not found.
                Logger.error("Failed to install ffmpeg. Please install manually") 
                Logger.info("Cannot transcode files in folder %s", dirName)
                return 1 # failure
            else:
                ffmpeg = 'ffmpeg'
        else:
            ffmpeg = 'ffmpeg'
    
    config = ConfigParser.ConfigParser()
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    Logger.info("Loading config from %s", configFilename)

    if not os.path.isfile(configFilename):
        Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
        return 1 # failure

    config.read(configFilename)
    
    mediaContainer = (config.get("Extensions", "mediaExtensions")).split(',')
    duplicate = int(config.get("Transcoder", "duplicate"))
    ignoreExtensions = (config.get("Transcoder", "ignoreExtensions")).split(',')
    outputVideoExtension = config.get("Transcoder", "outputVideoExtension")
    outputVideoCodec = config.get("Transcoder", "outputVideoCodec")
    outputVideoPreset = config.get("Transcoder", "outputVideoPreset")
    outputVideoFramerate = config.get("Transcoder", "outputVideoFramerate")
    outputVideoBitrate = config.get("Transcoder", "outputVideoBitrate")
    outputAudioCodec = config.get("Transcoder", "outputAudioCodec")
    outputAudioBitrate = config.get("Transcoder", "outputAudioBitrate")
    
    Logger.info("Checking for files to be transcoded")
    final_result = 0 # initialize as successful
    for dirpath, dirnames, filenames in os.walk(dirName):
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            name, ext = os.path.splitext(filePath)
            if ext in mediaContainer:  # If the file is a video file
                if ext in ignoreExtensions:
                    Logger.info("No need to transcode video type %s", ext)
                    continue
                if ext == outputVideoExtension: # we need to change the name to prevent overwriting itself.
                    outputVideoExtension = '-transcoded' + outputVideoExtension # adds '-transcoded.ext'
                newfilePath = os.path.normpath(name + outputVideoExtension)
        
                command = [ffmpeg, '-i', filePath]
                if outputVideoCodec:
                    command.append('-c:v')
                    command.append(outputVideoCodec)
                    if outputVideoCodec == 'libx264' and outputVideoPreset:
                        command.append('-preset')
                        command.append(outputVideoPreset)
                if outputVideoFramerate:
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
                # this will be 0 (successful) it all are sucessful, else will return a positive integer for failure.
                final_result = final_result + result 
    return final_result
