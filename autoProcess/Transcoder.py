import sys
import os
import ConfigParser
import logging
from subprocess import call

Logger = logging.getLogger()

def Transcode_directory(dirName):
    
    if os.name == 'nt':
        ffmpeg = os.path.join(os.path.dirname(sys.argv[0]), 'ffmpeg\\bin\\ffmpeg.exe') # note, will need to package in this dir.
        useNiceness = False
        if not os.path.isfile(ffmpeg): # problem
            Logger.error("ffmpeg not found. ffmpeg needs to be located at: %s", ffmpeg) 
            Logger.info("Cannot transcode files in folder %s", dirName)
            return 1 # failure
    else:
        if call(['which', 'ffmpeg']) != 0:
            res = call([os.path.join(os.path.dirname(sys.argv[0]),'getffmpeg.sh')])
            if res or call(['which', 'ffmpeg']) != 0: # did not install or ffmpeg still not found.
                Logger.error("Failed to install ffmpeg. Please install manually") 
                Logger.info("Cannot transcode files in folder %s", dirName)
                return 1 # failure
            else:
                ffmpeg = 'ffmpeg'
        else:
            ffmpeg = 'ffmpeg'
        useNiceness = True
    
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
    outputVideoExtension = config.get("Transcoder", "outputVideoExtension").strip()
    outputVideoCodec = config.get("Transcoder", "outputVideoCodec").strip()
    outputVideoPreset = config.get("Transcoder", "outputVideoPreset").strip()
    outputVideoFramerate = config.get("Transcoder", "outputVideoFramerate").strip()
    outputVideoBitrate = config.get("Transcoder", "outputVideoBitrate").strip()
    outputAudioCodec = config.get("Transcoder", "outputAudioCodec").strip()
    outputAudioBitrate = config.get("Transcoder", "outputAudioBitrate").strip()
    outputSubtitleCodec = config.get("Transcoder", "outputSubtitleCodec").strip()
    outputFastStart = int(config.get("Transcoder", "outputFastStart"))
    outputQualityPercent = int(config.get("Transcoder", "outputQualityPercent"))
    if useNiceness:
        niceness = int(config.get("Transcoder", "niceness"))

    map(lambda ext: ext.strip(), mediaContainer)
    map(lambda ext: ext.strip(), ignoreExtensions)
    
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

                command = [ffmpeg, '-loglevel', 'warning', '-i', filePath, '-map', '0']

                if useNiceness:
                    command = ['nice', '-%d' % niceness] + command

                if len(outputVideoCodec) > 0:
                    command.append('-c:v')
                    command.append(outputVideoCodec)
                    if outputVideoCodec == 'libx264' and outputVideoPreset:
                        command.append('-preset')
                        command.append(outputVideoPreset)
                else:
                    command.append('-c:v')
                    command.append('copy')
                if len(outputVideoFramerate) > 0:
                    command.append('-r')
                    command.append(outputVideoFramerate)
                if len(outputVideoBitrate) > 0:
                    command.append('-b:v')
                    command.append(outputVideoBitrate)
                if len(outputAudioCodec) > 0:
                    command.append('-c:a')
                    command.append(outputAudioCodec)
                    if outputAudioCodec == 'aac': # Allow users to use the experimental AAC codec that's built into recent versions of ffmpeg
                        command.append('-strict')
                        command.append('-2')
                else:
                    command.append('-c:a')
                    command.append('copy')
                if len(outputAudioBitrate) > 0:
                    command.append('-b:a')
                    command.append(outputAudioBitrate)
                if len(outputSubtitleCodec) > 0:
                    command.append('-c:s')
                    command.append(outputSubtitleCodec)
                if outputFastStart > 0:
                    command.append('-movflags')
                    command.append('+faststart')
                if outputQualityPercent > 0:
                    command.append('-q:a')
                    command.append(outputQualityPercent)
                else:
                    command.append('-sn')  # Don't copy the subtitles over
                command.append(newfilePath)
                
                try: # Try to remove the file that we're transcoding to just in case. (ffmpeg will return an error if it already exists for some reason)
                    os.remove(newFilePath)
                except OSError, e:
                    if e.errno != errno.ENOENT: # Ignore the error if it's just telling us that the file doesn't exist
                        Logger.debug("Error when removing transcoding target: %s", e)
                except Exception, e:
                    Logger.debug("Error when removing transcoding target: %s", e)

                Logger.info("Transcoding video: %s", file)
                result = 1 # set result to failed in case call fails.
                try:
                    result = call(command)
                except:
                    Logger.exception("Transcoding of video %s has failed", filePath)
                if result == 0:
                    Logger.info("Transcoding of video %s to %s succeded", filePath, newfilePath)
                    if duplicate == 0: # we get rid of the original file
                        os.unlink(filePath)
                else:
                    Logger.error("Transcoding of video %s to %s failed", filePath, newfilePath)
                # this will be 0 (successful) it all are sucessful, else will return a positive integer for failure.
                final_result = final_result + result 
    return final_result
