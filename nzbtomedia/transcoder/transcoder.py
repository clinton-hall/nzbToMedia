import errno
import os
import platform
import subprocess
import urllib2
import traceback
import nzbtomedia
import json
from subprocess import call
from nzbtomedia import logger
from nzbtomedia.nzbToMediaUtil import makeDir

def isVideoGood(videofile, status):
    fileNameExt = os.path.basename(videofile)
    fileName, fileExt = os.path.splitext(fileNameExt)
    if fileExt not in nzbtomedia.MEDIACONTAINER or not nzbtomedia.FFPROBE:
        if status:  # if the download was "failed", assume bad. If it was successful, assume good.
            return False
        else:
            return True

    logger.info('Checking [%s] for corruption, please stand by ...' % (fileNameExt), 'TRANSCODER')
    video_details, result = getVideoDetails(videofile)

    if result != 0:
        logger.error("FAILED: [%s] is corrupted!" % (fileNameExt), 'TRANSCODER')
        return False
    if video_details.get("error"):
        logger.info("FAILED: [%s] returned error [%s]." % (fileNameExt, str(video_details.get("error"))), 'TRANSCODER')
        return False
    if video_details.get("streams"):
        videoStreams = [item for item in video_details["streams"] if item["codec_type"] == "video"]
        audioStreams = [item for item in video_details["streams"] if item["codec_type"] == "audio"]
        if len(videoStreams) > 0 and len(audioStreams) > 0:
            logger.info("SUCCESS: [%s] has no corruption." % (fileNameExt), 'TRANSCODER')
            return True
        else:
            logger.info("FAILED: [%s] has %s video streams and %s audio streams. Assume corruption." % (fileNameExt, str(len(videoStreams)), str(len(audioStreams))), 'TRANSCODER')
            return False

def getVideoDetails(videofile):
    video_details = {}
    result = 1
    if not nzbtomedia.FFPROBE:
        return video_details, result
    try:
        command = [nzbtomedia.FFPROBE, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', '-show_error', videofile]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        result = proc.returncode
        video_details = json.loads(out)
    except: pass
    if not video_details:
        try:
            command = [nzbtomedia.FFPROBE, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', videofile]
            proc = subprocess.Popen(command, stdout=subprocess.PIPE)
            out, err = proc.communicate()
            result = proc.returncode
            video_details = json.loads(out)
        except:
            logger.error("Checking [%s] has failed" % (videofile), 'TRANSCODER')
    return video_details, result

def buildCommands(file, newDir):
    video_details, result = getVideoDetails(file)
    dir, name = os.path.split(file)
    name, ext = os.path.splitext(name)
    if ext == nzbtomedia.VEXTENSION and newDir == dir: # we need to change the name to prevent overwriting itself.
        nzbtomedia.VEXTENSION = '-transcoded' + nzbtomedia.VEXTENSION # adds '-transcoded.ext'

    newfilePath = os.path.normpath(os.path.join(newDir, name) + nzbtomedia.VEXTENSION)

    map_cmd = []
    video_cmd = []
    audio_cmd = []
    sub_cmd = []
    other_cmd = []

    if not video_details or not video_details.get("streams"):  # we couldn't read streams with ffprobe. Set defaults to try transcoding.
        videoStreams = []
        audioStreams = []
        subStreams = []

        map_cmd.extend(['-map', '0'])
        if nzbtomedia.VCODEC:
            video_cmd.extend(['-c:v', nzbtomedia.VCODEC])
            if nzbtomedia.VCODEC == 'libx264' and nzbtomedia.VPRESET:
                video_cmd.extend(['-pre', nzbtomedia.VPRESET])
        else:
            video_cmd.extend(['-c:v', 'copy'])
        if nzbtomedia.VFRAMERATE:
            video_cmd.extend(['-r', str(nzbtomedia.VFRAMERATE)])
        if nzbtomedia.VBITRATE:
            video_cmd.extend(['-b:v', str(nzbtomedia.VBITRATE)])
        if nzbtomedia.VRESOLUTION:
            video_cmd.extend(['-vf', 'scale=' + nzbtomedia.VRESOLUTION])

        if nzbtomedia.ACODEC:
            audio_cmd.extend(['-c:a', nzbtomedia.ACODEC])
            if nzbtomedia.ACODEC == 'aac': # Allow users to use the experimental AAC codec that's built into recent versions of ffmpeg
                audio_cmd.extend(['-strict', '-2'])
        else:
            audio_cmd.extend(['-c:a', 'copy'])
        if nzbtomedia.ACHANNELS:
                audio_cmd.extend(['-ac', str(nzbtomedia.ACHANNELS)])
        if nzbtomedia.ABITRATE:
            audio_cmd.extend(['-b:a', str(nzbtomedia.ABITRATE)])
        if nzbtomedia.OUTPUTQUALITYPERCENT:
            audio_cmd.extend(['-q:a', str(nzbtomedia.OUTPUTQUALITYPERCENT)])

        if nzbtomedia.SCODEC and nzbtomedia.ALLOWSUBS:
            sub_cmd.extend(['-c:s', nzbtomedia.SCODEC])
        elif nzbtomedia.ALLOWSUBS:  # Not every subtitle codec can be used for every video container format!
            sub_cmd.extend(['-c:s', 'copy'])
        else:  # http://en.wikibooks.org/wiki/FFMPEG_An_Intermediate_Guide/subtitle_options
            sub_cmd.extend('-sn')  # Don't copy the subtitles over
  
        if nzbtomedia.OUTPUTFASTSTART:
            other_cmd.extend(['-movflags', '+faststart'])

    else:
        videoStreams = [item for item in video_details["streams"] if item["codec_type"] == "video"]
        audioStreams = [item for item in video_details["streams"] if item["codec_type"] == "audio"]
        subStreams = [item for item in video_details["streams"] if item["codec_type"] == "subtitle"]
  

    for video in videoStreams:
        codec = video["codec_name"]
        fr = video["avg_frame_rate"]
        width = video["width"]
        height = video["height"]
        scale = nzbtomedia.VRESOLUTION
        try:
            framerate = float(fr.split('/')[0])/float(fr.split('/')[1])
        except:
            framerate = 0
        vid_cmds = []
        if codec in nzbtomedia.VCODEC_ALLOW or not nzbtomedia.VCODEC:
            video_cmd.extend(['-c:v', 'copy'])
        else:
            video_cmd.extend(['-c:v', nzbtomedia.VCODEC])
        if nzbtomedia.VFRAMERATE and not (nzbtomedia.VFRAMERATE * 0.999 <= fr <= nzbtomedia.VFRAMERATE * 1.001):
            video_cmd.extend(['-r', str(nzbtomedia.VFRAMERATE)])
        if scale:
            w_scale = width/int(scale.split(':')[0])
            h_scale = height/int(scale.split(':')[1])
            if w_scale > h_scale: # widescreen, Scale by width only.
               scale = scale.split(':')[0] + ":-1"
               if w_scale != 1:
                   video_cmd.extend(['-vf', 'scale=' + scale])
            else:  # lower or mathcing ratio, scale by height only.
               scale = "-1:" + scale.split(':')[1]
               if h_scale != 1:
                   video_cmd.extend(['-vf', 'scale=' + scale])        
        map_cmd.extend(['-map', '0:' + str(video["index"])])
        break  # Only one video needed

    used_audio = 0
    a_mapped = []
    if audioStreams:
        try:
            audio1 = [ item for item in audioStreams if item["tags"]["language"] == nzbtomedia.ALANGUAGE ]
        except:  # no language tags. Assume only 1 language.
            audio1 = audioStreams
        audio2 = [ item for item in audio1 if item["codec_name"] in nzbtomedia.ACODEC_ALLOW ]
        try:
            audio3 = [ item for item in audioStreams if item["tags"]["language"] != nzbtomedia.ALANGUAGE ]
        except:
            audio3 = []

        if audio2:  # right language and codec...
            map_cmd.extend(['-map', '0:' + str(audio2[0]["index"])])
            a_mapped.extend([audio2[0]["index"]])
            bitrate = int(audio2[0]["bit_rate"])/1000
            channels = int(audio2[0]["channels"])
            audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
        elif audio1:  # right language wrong codec.
            map_cmd.extend(['-map', '0:' + str(audio1[0]["index"])])
            a_mapped.extend([audio1[0]["index"]])
            bitrate = int(audio1[0]["bit_rate"])/1000
            channels = int(audio1[0]["channels"])
            if nzbtomedia.ACODEC:
                audio_cmd.extend(['-c:a:' + str(used_audio), nzbtomedia.ACODEC])
            else:
                audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
            if nzbtomedia.ACODEC == 'aac':
                audio_cmd.extend(['-strict', '-2'])
        elif audio3:  # just pick the default audio track
            map_cmd.extend(['-map', '0:' + str(audio3[0]["index"])])
            a_mapped.extend([audio3[0]["index"]])
            bitrate = int(audio3[0]["bit_rate"])/1000
            channels = int(audio3[0]["channels"])
            if nzbtomedia.ACODEC:
                audio_cmd.extend(['-c:a:' + str(used_audio), nzbtomedia.ACODEC])
            else:
                audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
            if nzbtomedia.ACODEC == 'aac':
                audio_cmd.extend(['-strict', '-2'])

        if nzbtomedia.ACHANNELS and channels > nzbtomedia.ACHANNELS:
            audio_cmd.extend(['-ac:' + str(used_audio), str(nzbtomedia.ACHANNELS)])
        if nzbtomedia.ABITRATE and not (nzbtomedia.ABITRATE * 0.9 < bitrate < nzbtomedia.ABITRATE * 1.1):
            audio_cmd.extend(['-b:a:' + str(used_audio), str(nzbtomedia.ABITRATE)])
        if nzbtomedia.OUTPUTQUALITYPERCENT:
            audio_cmd.extend(['-q:a:' + str(used_audio), str(nzbtomedia.OUTPUTQUALITYPERCENT)])

        if nzbtomedia.ACODEC2_ALLOW:
            used_audio += 1
            audio4 = [ item for item in audio1 if item["codec_name"] in nzbtomedia.ACODEC2_ALLOW ]
            if audio4:  # right language and codec.
                map_cmd.extend(['-map', '0:' + str(audio4[0]["index"])])
                a_mapped.extend([audio4[0]["index"]])
                bitrate = int(audio4[0]["bit_rate"])/1000
                channels = int(audio4[0]["channels"])
                audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
            elif audio1:  # right language wrong codec.
                map_cmd.extend(['-map', '0:' + str(audio1[0]["index"])])
                a_mapped.extend([audio1[0]["index"]])
                bitrate = int(audio1[0]["bit_rate"])/1000
                channels = int(audio1[0]["channels"])
                if nzbtomedia.ACODEC2:
                    audio_cmd.extend(['-c:a:' + str(used_audio), nzbtomedia.ACODEC2])
                else:
                    audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
                if nzbtomedia.ACODEC2 == 'aac':
                    audio_cmd.extend(['-strict', '-2'])
            elif audio3:  # just pick the default audio track
                map_cmd.extend(['-map', '0:' + str(audio3[0]["index"])])
                a_mapped.extend([audio3[0]["index"]])
                bitrate = int(audio3[0]["bit_rate"])/1000
                channels = int(audio3[0]["channels"])
                if nzbtomedia.ACODEC2:
                    audio_cmd.extend(['-c:a:' + str(used_audio), nzbtomedia.ACODEC2])
                else:
                    audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
                if nzbtomedia.ACODEC2 == 'aac':
                    audio_cmd.extend(['-strict', '-2'])

            if nzbtomedia.ACHANNELS2 and channels > nzbtomedia.ACHANNELS2:
                audio_cmd.extend(['-ac:' + str(used_audio), str(nzbtomedia.ACHANNELS2)])
            if nzbtomedia.ABITRATE2 and not (nzbtomedia.ABITRATE2 * 0.9 < bitrate < nzbtomedia.ABITRATE2 * 1.1):
                audio_cmd.extend(['-b:a' + str(used_audio), str(nzbtomedia.ABITRATE2)])
            if nzbtomedia.OUTPUTQUALITYPERCENT:
                audio_cmd.extend(['-q:a' + str(used_audio), str(nzbtomedia.OUTPUTQUALITYPERCENT)])

        if nzbtomedia.AINCLUDE and audio3 and nzbtomedia.ACODEC3:
            for audio in audioStreams:
                if audio["index"] in a_mapped:
                    continue
                used_audio += 1
                map_cmd.extend(['-map', '0:' + str(audio["index"])])
                bitrate = int(audio["bit_rate"])/1000
                channels = int(audio["channels"])
                if audio["codec_name"] in nzbtomedia.ACODEC3_ALLOW:
                    audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
                else:
                    if nzbtomedia.ACODEC3:
                        audio_cmd.extend(['-c:a:' + str(used_audio), nzbtomedia.ACODEC3])
                    else:
                        audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
                    if nzbtomedia.ACODEC3 == 'aac':
                        audio_cmd.extend(['-strict', '-2'])
                if nzbtomedia.ACHANNELS3 and channels > nzbtomedia.ACHANNELS3:
                    audio_cmd.extend(['-ac:' + str(used_audio), str(nzbtomedia.ACHANNELS3)])
                if nzbtomedia.ABITRATE3 and not (nzbtomedia.ABITRATE3 * 0.9 < bitrate < nzbtomedia.ABITRATE3 * 1.1):
                    audio_cmd.extend(['-b:a:' + str(used_audio), str(nzbtomedia.ABITRATE3)])
                if nzbtomedia.OUTPUTQUALITYPERCENT > 0:
                    audio_cmd.extend(['-q:a:' + str(used_audio), str(nzbtomedia.OUTPUTQUALITYPERCENT)])

    s_mapped = []
    subs1 = []
    burnt = 0
    for lan in nzbtomedia.SLANGUAGES:
        subs1 = [ item for item in subStreams if item["tags"]["language"] == lan ]
        if nzbtomedia.BURN and not subs1 and not burnt:
            for subfile in get_subs(file):
                if lan in os.path.split(subfile)[1]:
                    video_cmd.extend(['-vf', 'subtitles=' + subfile])
                    burnt = 1
        for sub in subs1:
            if nzbtomedia.BURN and not burnt:
                subloc = 0
                for index in range(len(subStreams)):
                    if sunStreams[index]["index"] == sub["index"]:
                        subloc = index
                        break
                video_cmd.extend(['-vf', 'subtitles=' + file + ":si=" + subloc])
                burnt = 1
            if not nzbtomedia.ALLOWSUBS:
                break
            map_cmd.extend(['-map', '0:' + str(sub["index"])])
            s_mapped.extend([sub["index"]])
            
    if nzbtomedia.SINCLUDE:
        for sub in subStreams:
            if not nzbtomedia.ALLOWSUBS:
                break
            if sub["index"] in s_mapped:
                continue
            map_cmd.extend(['-map', '0:' + str(sub["index"])])
            s_mapped.extend([sub["index"]]) 
    if not nzbtomedia.ALLOWSUBS:
        sub_cmd.extend('-sn')
    else:       
        if nzbtomedia.SCODEC:
            sub_cmd.extend(['-c:s', nzbtomedia.SCODEC])
        else:
            sub_cmd.extend(['-c:s', 'copy'])

    if nzbtomedia.OUTPUTFASTSTART:
        other_cmd.extend(['-movflags', '+faststart'])

    command = [nzbtomedia.FFMPEG, '-loglevel', 'warning', '-i', file]

    if nzbtomedia.SEMBED:
        filenum = 1
        for subfile in get_subs(file):
            command.extend(['-i', subfile])
            map_cmd.extend(['-map', n])
            n += 1

    command.extend(map_cmd)
    command.extend(video_cmd)
    command.extend(audio_cmd)
    command.extend(sub_cmd)
    command.extend(other_cmd)
    command.append(newfilePath)
    if platform.system() != 'Windows':
        command = nzbtomedia.NICENESS + command
    return command

def get_subs(file):
    filepaths = []
    subExt = ['.srt', '.sub', '.idx']
    name = os.path.splitext(os.path.split(file)[1])[0]
    dir = os.path.split(file)[0]
    for dirname, dirs, filenames in os.walk(dir):
        for filename in filenames:
            filepaths.extend([os.path.join(dirname, filename)])
    subfiles = [ item for item in filepaths if os.path.splitext(item)[1] in subExt and name in item ]
    return subfiles

def extract_subs(file, newfilePath, bitbucket):
    video_details = getVideoDetails(file)
    if not video_details:
        return
    subStreams = [item for item in video_details["streams"] if item["codec_type"] == "subtitle"]
    if nzbtomedia.SUBSDIR:
        subdir = nzbtomedia.SUBSDIR
    else:
        subdir = os.path.split(newfilePath)[0]
    name = os.path.splitext(os.path.split(newfilePath)[1])[0]
    for n in range(len(subStreams)):
        sub = subStreams[n]
        lan = sub["tags"]["language"]
        outputFile = os.path.join(subdir, "%s(%s).srt" %(name, lan))
        if os.path.isfile(outputFile):
            outputFile = os.path.join(subdir, "%s(%s)%s.srt" %(name, n, lan))
        command = [nzbtomedia.FFMPEG, '-loglevel', 'warning', '-i', sub, '-vn', '-an', '-codec:s:' + str(n), 'srt', outputFile]
        if platform.system() != 'Windows':
            command = nzbtomedia.NICENESS + command

        logger.info("Extracting %s Subtitle from: %s" % (lan, file))
        cmd = ""
        for item in command:
            cmd = cmd + " " + item
        logger.debug("calling command:%s" % (cmd))
        result = 1 # set result to failed in case call fails.
        try:
            result = call(command, stdout=bitbucket, stderr=bitbucket)
        except:
            logger.error("Extracting subtitles has failed")

        if result == 0:
            logger.info("Extracting %s Subtitle from %s has succeeded" % (lan, file))
        else:
            logger.error("Extracting subtitles has failed")
        

def Transcode_directory(dirName):
    if platform.system() == 'Windows':
        bitbucket = open('NUL')
    else:
        bitbucket = open('/dev/null')

    if not nzbtomedia.FFMPEG:
        return 1

    logger.info("Checking for files to be transcoded")
    final_result = 0 # initialize as successful
    if nzbtomedia.OUTPUTVIDEOPATH:
        newDir = nzbtomedia.OUTPUTVIDEOPATH
        makeDir(newDir)
    else:
        newDir = dirName
    for file in nzbtomedia.listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False):
        if os.path.splitext(file)[1] in nzbtomedia.IGNOREEXTENSIONS:
            continue
        command = buildCommands(file, newDir)
        newfilePath = command[-1]
        try: # Try to remove the file that we're transcoding to just in case. (ffmpeg will return an error if it already exists for some reason)
            os.remove(newfilePath)
        except OSError, e:
            if e.errno != errno.ENOENT: # Ignore the error if it's just telling us that the file doesn't exist
                logger.debug("Error when removing transcoding target: %s" % (e))
        except Exception, e:
            logger.debug("Error when removing transcoding target: %s" % (e))

        logger.info("Transcoding video: %s" % (file))
        cmd = ""
        for item in command:
            cmd = cmd + " " + item
        logger.debug("calling command:%s" % (cmd))
        result = 1 # set result to failed in case call fails.
        try:
            result = call(command, stdout=bitbucket, stderr=bitbucket)
        except:
            logger.error("Transcoding of video %s has failed" % (file))

        if result == 0:
            logger.info("Transcoding of video %s to %s succeeded" % (file, newfilePath))
            if not nzbtomedia.DUPLICATE and os.path.isfile(newfilePath): # we get rid of the original file
                os.unlink(file)
        else:
            logger.error("Transcoding of video %s to %s failed" % (file, newfilePath))
        # this will be 0 (successful) it all are successful, else will return a positive integer for failure.
        final_result = final_result + result
        if nzbtomedia.SEXTRACT:
            extract_subs(file, newfilePath, bitbucket)
        if nzbtomedia.SUBSDIR:
            for sub in get_subs(file):
                name = os.path.splitext(os.path.split(file)[1])[0]
                subname = os.path.split(sub)[1]
                newname = os.path.splitext(os.path.split(newfilePath)[1])[0]
                newpath = os.path.join(nzbtomedia.SUBSDIR, subname.replace(name, newname))
                if not os.path.isfile(newpath):
                    os.rename(sub, newpath)

    if not nzbtomedia.PROCESSOUTPUT and nzbtomedia.DUPLICATE:  # We postprocess the original files to CP/SB 
        newDir = dirName
    return final_result, newDir
