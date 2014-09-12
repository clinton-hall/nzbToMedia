import errno
import os
import platform
import subprocess
import urllib2
import traceback
import nzbtomedia
import json
import shutil
import re
from subprocess import call
from nzbtomedia import logger
from nzbtomedia.nzbToMediaUtil import makeDir

def isVideoGood(videofile, status):
    fileNameExt = os.path.basename(videofile)
    fileName, fileExt = os.path.splitext(fileNameExt)
    disable = False
    if fileExt not in nzbtomedia.MEDIACONTAINER or not nzbtomedia.FFPROBE or not nzbtomedia.CHECK_MEDIA or fileExt in ['.iso']:
        disable = True
    else:
        test_details, res = getVideoDetails(nzbtomedia.TEST_FILE)
        if res !=0 or test_details.get("error"):
            disable = True
            logger.info("DISABLED: ffprobe failed to analyse test file. Stopping corruption check.", 'TRANSCODER')
        if test_details.get("streams"):
            vidStreams = [item for item in test_details["streams"] if item["codec_type"] == "video"]
            audStreams = [item for item in test_details["streams"] if item["codec_type"] == "audio"]
            if not (len(vidStreams) > 0 and len(audStreams) > 0):
                disable = True
                logger.info("DISABLED: ffprobe failed to analyse streams from test file. Stopping corruption check.", 'TRANSCODER')
    if disable:
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
    if 'avprobe' in nzbtomedia.FFPROBE:
        print_format = '-of'
    else:
        print_format = '-print_format'
    try:
        command = [nzbtomedia.FFPROBE, '-v', 'quiet', print_format, 'json', '-show_format', '-show_streams', '-show_error', videofile]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        result = proc.returncode
        video_details = json.loads(out)
    except: pass
    if not video_details:
        try:
            command = [nzbtomedia.FFPROBE, '-v', 'quiet', print_format, 'json', '-show_format', '-show_streams', videofile]
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
            sub_cmd.extend(['-sn'])  # Don't copy the subtitles over
  
        if nzbtomedia.OUTPUTFASTSTART:
            other_cmd.extend(['-movflags', '+faststart'])

    else:
        videoStreams = [item for item in video_details["streams"] if item["codec_type"] == "video"]
        audioStreams = [item for item in video_details["streams"] if item["codec_type"] == "audio"]
        subStreams = [item for item in video_details["streams"] if item["codec_type"] == "subtitle"]
        if nzbtomedia.VEXTENSION not in ['.mkv', '.mpegts']:
            subStreams = [item for item in video_details["streams"] if item["codec_type"] == "subtitle" and item["codec_name"] != "hdmv_pgs_subtitle" and item["codec_name"] != "pgssub"]

    for video in videoStreams:
        codec = video["codec_name"]
        try:
            fr = video["avg_frame_rate"]
        except: fr = 0
        try:
            width = video["width"]
        except: width = 0
        try:
            height = video["height"]
        except: height = 0
        scale = nzbtomedia.VRESOLUTION
        try:
            framerate = float(fr.split('/')[0])/float(fr.split('/')[1])
        except: framerate = 0
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
        if ('-vf' in video_cmd or '-r' in video_cmd) and video_cmd[1] == 'copy':
            video_cmd[1] = nzbtomedia.VCODEC
        if nzbtomedia.VCODEC == 'copy':  # force copy. therefore ignore all other video transcoding.
            video_cmd = ['-c:v', 'copy']  
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
            try:
                bitrate = int(audio2[0]["bit_rate"])/1000
            except: bitrate = 0
            try:
                channels = int(audio2[0]["channels"])
            except: channels = 0
            audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
        elif audio1:  # right language wrong codec.
            map_cmd.extend(['-map', '0:' + str(audio1[0]["index"])])
            a_mapped.extend([audio1[0]["index"]])
            try:
                bitrate = int(audio1[0]["bit_rate"])/1000
            except: bitrate = 0
            try:
                channels = int(audio1[0]["channels"])
            except: channels = 0
            if nzbtomedia.ACODEC:
                audio_cmd.extend(['-c:a:' + str(used_audio), nzbtomedia.ACODEC])
            else:
                audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
            if nzbtomedia.ACODEC == 'aac':
                audio_cmd.extend(['-strict', '-2'])
        elif audio3:  # just pick the default audio track
            map_cmd.extend(['-map', '0:' + str(audio3[0]["index"])])
            a_mapped.extend([audio3[0]["index"]])
            try:
                bitrate = int(audio3[0]["bit_rate"])/1000
            except: bitrate = 0
            try:
                channels = int(audio3[0]["channels"])
            except: channels = 0
            if nzbtomedia.ACODEC:
                audio_cmd.extend(['-c:a:' + str(used_audio), nzbtomedia.ACODEC])
            else:
                audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
            if nzbtomedia.ACODEC == 'aac':
                audio_cmd.extend(['-strict', '-2'])

        if nzbtomedia.ACHANNELS and channels and channels > nzbtomedia.ACHANNELS:
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
                try:
                    bitrate = int(audio4[0]["bit_rate"])/1000
                except: bitrate = 0
                try:
                    channels = int(audio4[0]["channels"])
                except: channels = 0
                audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
            elif audio1:  # right language wrong codec.
                map_cmd.extend(['-map', '0:' + str(audio1[0]["index"])])
                a_mapped.extend([audio1[0]["index"]])
                try:
                    bitrate = int(audio1[0]["bit_rate"])/1000
                except: bitrate = 0
                try:
                    channels = int(audio1[0]["channels"])
                except: channels = 0
                if nzbtomedia.ACODEC2:
                    audio_cmd.extend(['-c:a:' + str(used_audio), nzbtomedia.ACODEC2])
                else:
                    audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
                if nzbtomedia.ACODEC2 == 'aac':
                    audio_cmd.extend(['-strict', '-2'])
            elif audio3:  # just pick the default audio track
                map_cmd.extend(['-map', '0:' + str(audio3[0]["index"])])
                a_mapped.extend([audio3[0]["index"]])
                try:
                    bitrate = int(audio3[0]["bit_rate"])/1000
                except: bitrate = 0
                try:
                    channels = int(audio3[0]["channels"])
                except: channels = 0
                if nzbtomedia.ACODEC2:
                    audio_cmd.extend(['-c:a:' + str(used_audio), nzbtomedia.ACODEC2])
                else:
                    audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
                if nzbtomedia.ACODEC2 == 'aac':
                    audio_cmd.extend(['-strict', '-2'])

            if nzbtomedia.ACHANNELS2 and channels and channels > nzbtomedia.ACHANNELS2:
                audio_cmd.extend(['-ac:' + str(used_audio), str(nzbtomedia.ACHANNELS2)])
            if nzbtomedia.ABITRATE2 and not (nzbtomedia.ABITRATE2 * 0.9 < bitrate < nzbtomedia.ABITRATE2 * 1.1):
                audio_cmd.extend(['-b:a:' + str(used_audio), str(nzbtomedia.ABITRATE2)])
            if nzbtomedia.OUTPUTQUALITYPERCENT:
                audio_cmd.extend(['-q:a:' + str(used_audio), str(nzbtomedia.OUTPUTQUALITYPERCENT)])

        if nzbtomedia.AINCLUDE and audio3 and nzbtomedia.ACODEC3:
            for audio in audioStreams:
                if audio["index"] in a_mapped:
                    continue
                used_audio += 1
                map_cmd.extend(['-map', '0:' + str(audio["index"])])
                try:
                    bitrate = int(audio["bit_rate"])/1000
                except: bitrate = 0
                try:
                    channels = int(audio["channels"])
                except: channels = 0
                if audio["codec_name"] in nzbtomedia.ACODEC3_ALLOW:
                    audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
                else:
                    if nzbtomedia.ACODEC3:
                        audio_cmd.extend(['-c:a:' + str(used_audio), nzbtomedia.ACODEC3])
                    else:
                        audio_cmd.extend(['-c:a:' + str(used_audio), 'copy'])
                    if nzbtomedia.ACODEC3 == 'aac':
                        audio_cmd.extend(['-strict', '-2'])
                if nzbtomedia.ACHANNELS3 and channels and channels > nzbtomedia.ACHANNELS3:
                    audio_cmd.extend(['-ac:' + str(used_audio), str(nzbtomedia.ACHANNELS3)])
                if nzbtomedia.ABITRATE3 and not (nzbtomedia.ABITRATE3 * 0.9 < bitrate < nzbtomedia.ABITRATE3 * 1.1):
                    audio_cmd.extend(['-b:a:' + str(used_audio), str(nzbtomedia.ABITRATE3)])
                if nzbtomedia.OUTPUTQUALITYPERCENT > 0:
                    audio_cmd.extend(['-q:a:' + str(used_audio), str(nzbtomedia.OUTPUTQUALITYPERCENT)])

    s_mapped = []
    subs1 = []
    burnt = 0
    n = 0
    for lan in nzbtomedia.SLANGUAGES:
        try:
            subs1 = [ item for item in subStreams if item["tags"]["language"] == lan ]
        except: subs1 = []
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
    if not nzbtomedia.ALLOWSUBS or not s_mapped:
        sub_cmd.extend(['-sn'])
    else:       
        if nzbtomedia.SCODEC:
            sub_cmd.extend(['-c:s', nzbtomedia.SCODEC])
        else:
            sub_cmd.extend(['-c:s', 'copy'])

    if nzbtomedia.OUTPUTFASTSTART:
        other_cmd.extend(['-movflags', '+faststart'])

    command = [nzbtomedia.FFMPEG, '-loglevel', 'warning']

    if nzbtomedia.HWACCEL:
        command.extend(['-hwaccel', 'auto'])
    if nzbtomedia.GENERALOPTS:
        command.extend(nzbtomedia.GENERALOPTS)

    command.extend([ '-i', file])

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
    video_details, result = getVideoDetails(file)
    if not video_details:
        return

    if nzbtomedia.SUBSDIR:
        subdir = nzbtomedia.SUBSDIR
    else:
        subdir = os.path.split(newfilePath)[0]
    name = os.path.splitext(os.path.split(newfilePath)[1])[0]

    try:
        subStreams = [item for item in video_details["streams"] if item["codec_type"] == "subtitle" and item["tags"]["language"] in nzbtomedia.SLANGUAGES and item["codec_name"] != "hdmv_pgs_subtitle" and item["codec_name"] != "pgssub"]
    except:
        subStreams = [item for item in video_details["streams"] if item["codec_type"] == "subtitle" and item["codec_name"] != "hdmv_pgs_subtitle" and item["codec_name"] != "pgssub"]
    num = len(subStreams)
    for n in range(num):
        sub = subStreams[n]
        idx = sub["index"]
        try:
          lan = sub["tags"]["language"]
        except:
          lan = "unk"

        if num == 1:
          outputFile = os.path.join(subdir, "%s.srt" %(name))
          if os.path.isfile(outputFile):
              outputFile = os.path.join(subdir, "%s.%s.srt" %(name, n))
        else:
          outputFile = os.path.join(subdir, "%s.%s.srt" %(name, lan))
          if os.path.isfile(outputFile):
              outputFile = os.path.join(subdir, "%s.%s.%s.srt" %(name, lan, n))

        command = [nzbtomedia.FFMPEG, '-loglevel', 'warning', '-i', file, '-vn', '-an', '-codec:' + str(idx), 'srt', outputFile]
        if platform.system() != 'Windows':
            command = nzbtomedia.NICENESS + command

        logger.info("Extracting %s subtitle from: %s" % (lan, file))
        print_cmd(command)
        result = 1 # set result to failed in case call fails.
        try:
            result = call(command, stdout=bitbucket, stderr=bitbucket)
        except:
            logger.error("Extracting subtitle has failed")

        if result == 0:
            try:
                shutil.copymode(file, outputFile)
            except: pass
            logger.info("Extracting %s subtitle from %s has succeeded" % (lan, file))
        else:
            logger.error("Extracting subtitles has failed")

def processList(List, newDir, name, bitbucket):
    remList = []
    newList = []
    delList = []
    vtsPath = None
    success = True
    for item in List:
        newfile = None
        if os.path.splitext(item)[1].lower() == '.iso' and not '.iso' in nzbtomedia.IGNOREEXTENSIONS:
            logger.debug("Attempting to rip .iso image: %s" % (item), "TRANSCODER")
            newList.extend(ripISO(item, newDir, name, bitbucket))
            remList.append(item)
        elif re.match(".+VTS_[0-9][0-9]_[0-9].[Vv][Oo][Bb]", item) and not '.vob' in nzbtomedia.IGNOREEXTENSIONS:
            logger.debug("Found VIDEO_TS image file: %s" % (item), "TRANSCODER")
            if not vtsPath:
                vtsPath = re.match(".+VIDEO_TS",item).group()
                if not vtsPath:
                    vtsPath = os.path.split(item)[0]
            remList.append(item)
        elif re.match(".+VIDEO_TS.", item) or re.match(".+VTS_[0-9][0-9]_[0-9].", item):
            remList.append(item)
        else: continue     
    if vtsPath:
        newList.extend(combineVTS(vtsPath, newDir, name, bitbucket))
    for file in newList:
        if not os.path.isfile(file):
            success = False
            break
    if success and newList:
        List.extend(newList)
        for item in remList:
            List.remove(item)
        logger.debug("Successfully extracted .vob file %s from disk image" % (newList[0]), "TRANSCODER")
    elif newList and not success:
        newList = []
        remList = []
        logger.error("Failed extracting .vob files from disk image. Stopping transcoding.", "TRANSCODER")
    return List, remList, newList, success 

def ripISO(item, newDir, name, bitbucket):
    newFiles = []
    failure_dir = '/this/is/not/real'

    # Mount the ISO in your OS and call combineVTS.
    if platform.system() == 'Windows':
        temp_iso = item  # pfm mounts in place.
        cmd = ['pfm', 'mount', item]
    else:
        temp_iso = os.path.join(newDir, 'tmp_iso')
        os.makedirs(temp_iso)
        cmd = ['mount', '-o',  'rw', 'loop', item, temp_iso]
    try:
        logger.debug("Attempting to mount .iso file %s to extract .vob" % (item), "TRANSCODER")
        print_cmd(cmd)
        result = call(cmd, stdout=bitbucket, stderr=bitbucket)
        if os.path.isdir(os.path.join(temp_iso, 'VIDEO_TS')):
            vtsPath = os.path.join(temp_iso, 'VIDEO_TS')
            newFiles.extend(combineVTS(vtsPath, newDir, name, bitbucket))
        else:
            logger.error("No VIDEO_TS folder found in .iso file %s" % (item), "TRANSCODER")
            newFiles = [failure_dir]
    except:
        logger.error("Failed to mount .iso file %s" % (item), "TRANSCODER")
        return [failure_dir]
    # Unmount and delete.
    if platform.system() == 'Windows':
        cmd = ['pfm', 'unmount', item]
    else:
        cmd = ['umount', temp_iso]
    try:
        logger.debug("Attempting to unmount .iso file %s" % (item), "TRANSCODER")
        print_cmd(cmd)
        result = call(cmd, stdout=bitbucket, stderr=bitbucket)
        if not platform.system() == 'Windows': 
            os.unlink(temp_iso)
    except:
        logger.error("Failed to unmount .iso file %s" % (item), "TRANSCODER") 
    return newFiles

def combineVTS(vtsPath, newDir, name, bitbucket):
    newFiles = []
    failure_dir = '/this/is/not/real'
    for n in range(99):
        files = []
        m = 1
        while True:
            if os.path.isfile(os.path.join(vtsPath, 'VTS_0%s_%s.VOB' % (str(n+1), str(m)))):
                files.append(os.path.join(vtsPath, 'VTS_0%s_%s.VOB' % (str(n+1), str(m))))
                m += 1
            else:
                break
        if not files:
            break
        logger.debug("Attempting to extract video track %s from disk image" % (str(n+1)), "TRANSCODER")
        newfile = os.path.join(newDir, '%s.cd%s.vob' % (name, str(n+1)))
        try:
            f = open(newfile, "wb")
            for file in files:
                shutil.copyfileobj(open(file, 'rb'), f)
            f.close()
            newFiles.append(newfile)
        except:
            logger.debug("Failed to extract video track %s from disk image" % (str(n+1)), "TRANSCODER")
            return [failure_dir]
    return newFiles

def print_cmd(command):
    cmd = ""
    for item in command:
        cmd = cmd + " " + str(item)
    logger.debug("calling command:%s" % (cmd))

def Transcode_directory(dirName):
    if not nzbtomedia.FFMPEG:
        return 1, dirName

    logger.info("Checking for files to be transcoded")
    final_result = 0 # initialize as successful
    if nzbtomedia.OUTPUTVIDEOPATH:
        newDir = nzbtomedia.OUTPUTVIDEOPATH
        makeDir(newDir)
    else:
        newDir = dirName
    if platform.system() == 'Windows':
        bitbucket = open('NUL')
    else:
        bitbucket = open('/dev/null')
    movieName = os.path.splitext(os.path.split(dirName)[1])[0]
    List = nzbtomedia.listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False)
    List, remList, newList, success = processList(List, newDir, movieName, bitbucket)
    if not success:
        bitbucket.close()
        return 1, dirName

    for file in List:
        if os.path.splitext(file)[1] in nzbtomedia.IGNOREEXTENSIONS:
            continue
        command = buildCommands(file, newDir)
        newfilePath = command[-1]

        # transcoding files may remove the original file, so make sure to extract subtitles first
        if nzbtomedia.SEXTRACT:
            extract_subs(file, newfilePath, bitbucket)

        try: # Try to remove the file that we're transcoding to just in case. (ffmpeg will return an error if it already exists for some reason)
            os.remove(newfilePath)
        except OSError, e:
            if e.errno != errno.ENOENT: # Ignore the error if it's just telling us that the file doesn't exist
                logger.debug("Error when removing transcoding target: %s" % (e))
        except Exception, e:
            logger.debug("Error when removing transcoding target: %s" % (e))

        logger.info("Transcoding video: %s" % (file))
        print_cmd(command)
        result = 1 # set result to failed in case call fails.
        try:
            result = call(command, stdout=bitbucket, stderr=bitbucket)
        except:
            logger.error("Transcoding of video %s has failed" % (file))

        if nzbtomedia.SUBSDIR and result == 0:
            for sub in get_subs(file):
                name = os.path.splitext(os.path.split(file)[1])[0]
                subname = os.path.split(sub)[1]
                newname = os.path.splitext(os.path.split(newfilePath)[1])[0]
                newpath = os.path.join(nzbtomedia.SUBSDIR, subname.replace(name, newname))
                if not os.path.isfile(newpath):
                    os.rename(sub, newpath)

        if result == 0:
            try:
                shutil.copymode(file, newfilePath)
            except: pass
            logger.info("Transcoding of video %s to %s succeeded" % (file, newfilePath))
            if os.path.isfile(newfilePath) and (file in newList or not nzbtomedia.DUPLICATE):
                try:
                    os.unlink(file)
                except: pass 
        else:
            logger.error("Transcoding of video %s to %s failed" % (file, newfilePath))
        # this will be 0 (successful) it all are successful, else will return a positive integer for failure.
        final_result = final_result + result
    if final_result == 0 and not nzbtomedia.DUPLICATE:
        for file in remList:
            try:
                os.unlink(file)
            except: pass
    if not nzbtomedia.PROCESSOUTPUT and nzbtomedia.DUPLICATE:  # We postprocess the original files to CP/SB 
        newDir = dirName
    bitbucket.close()
    return final_result, newDir
