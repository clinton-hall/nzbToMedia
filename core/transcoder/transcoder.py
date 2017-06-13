# coding=utf-8

from six import iteritems
import errno
import os
import platform
import subprocess
import core
import json
import shutil
import re
from core import logger
from core.nzbToMediaUtil import makeDir
from babelfish import Language


def isVideoGood(videofile, status):
    fileNameExt = os.path.basename(videofile)
    fileName, fileExt = os.path.splitext(fileNameExt)
    disable = False
    if fileExt not in core.MEDIACONTAINER or not core.FFPROBE or not core.CHECK_MEDIA or fileExt in ['.iso']:
        disable = True
    else:
        test_details, res = getVideoDetails(core.TEST_FILE)
        if res != 0 or test_details.get("error"):
            disable = True
            logger.info("DISABLED: ffprobe failed to analyse test file. Stopping corruption check.", 'TRANSCODER')
        if test_details.get("streams"):
            vidStreams = [item for item in test_details["streams"] if "codec_type" in item and item["codec_type"] == "video"]
            audStreams = [item for item in test_details["streams"] if "codec_type" in item and item["codec_type"] == "audio"]
            if not (len(vidStreams) > 0 and len(audStreams) > 0):
                disable = True
                logger.info("DISABLED: ffprobe failed to analyse streams from test file. Stopping corruption check.",
                            'TRANSCODER')
    if disable:
        if status:  # if the download was "failed", assume bad. If it was successful, assume good.
            return False
        else:
            return True

    logger.info('Checking [{0}] for corruption, please stand by ...'.format(fileNameExt), 'TRANSCODER')
    video_details, result = getVideoDetails(videofile)

    if result != 0:
        logger.error("FAILED: [{0}] is corrupted!".format(fileNameExt), 'TRANSCODER')
        return False
    if video_details.get("error"):
        logger.info("FAILED: [{0}] returned error [{1}].".format(fileNameExt, video_details.get("error")), 'TRANSCODER')
        return False
    if video_details.get("streams"):
        videoStreams = [item for item in video_details["streams"] if item["codec_type"] == "video"]
        audioStreams = [item for item in video_details["streams"] if item["codec_type"] == "audio"]
        if len(videoStreams) > 0 and len(audioStreams) > 0:
            logger.info("SUCCESS: [{0}] has no corruption.".format(fileNameExt), 'TRANSCODER')
            return True
        else:
            logger.info("FAILED: [{0}] has {1} video streams and {2} audio streams. "
                        "Assume corruption.".format
                        (fileNameExt, len(videoStreams), len(audioStreams)), 'TRANSCODER')
            return False


def zip_out(file, img, bitbucket):
    procin = None
    cmd = [core.SEVENZIP, '-so', 'e', img, file]
    try:
        procin = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=bitbucket)
    except:
        logger.error("Extracting [{0}] has failed".format(file), 'TRANSCODER')
    return procin


def getVideoDetails(videofile, img=None, bitbucket=None):
    video_details = {}
    result = 1
    file = videofile
    if not core.FFPROBE:
        return video_details, result
    if 'avprobe' in core.FFPROBE:
        print_format = '-of'
    else:
        print_format = '-print_format'
    try:
        if img:
            videofile = '-'
        command = [core.FFPROBE, '-v', 'quiet', print_format, 'json', '-show_format', '-show_streams', '-show_error',
                   videofile]
        print_cmd(command)
        if img:
            procin = zip_out(file, img, bitbucket)
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=procin.stdout)
            procin.stdout.close()
        else:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        result = proc.returncode
        video_details = json.loads(out)
    except:
        pass
    if not video_details:
        try:
            command = [core.FFPROBE, '-v', 'quiet', print_format, 'json', '-show_format', '-show_streams', videofile]
            if img:
                procin = zip_out(file, img)
                proc = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=procin.stdout)
                procin.stdout.close()
            else:
                proc = subprocess.Popen(command, stdout=subprocess.PIPE)
            out, err = proc.communicate()
            result = proc.returncode
            video_details = json.loads(out)
        except:
            logger.error("Checking [{0}] has failed".format(file), 'TRANSCODER')
    return video_details, result


def buildCommands(file, newDir, movieName, bitbucket):
    if isinstance(file, basestring):
        inputFile = file
        if 'concat:' in file:
            file = file.split('|')[0].replace('concat:', '')
        video_details, result = getVideoDetails(file)
        dir, name = os.path.split(file)
        name, ext = os.path.splitext(name)
        check = re.match("VTS_([0-9][0-9])_[0-9]+", name)
        if check and core.CONCAT:
            name = movieName
        elif check:
            name = ('{0}.cd{1}'.format(movieName, check.groups()[0]))
        elif core.CONCAT and re.match("(.+)[cC][dD][0-9]", name):
            name = re.sub("([\ \.\-\_\=\:]+[cC][dD][0-9])", "", name)
        if ext == core.VEXTENSION and newDir == dir:  # we need to change the name to prevent overwriting itself.
            core.VEXTENSION = '-transcoded{ext}'.format(ext=core.VEXTENSION)  # adds '-transcoded.ext'
    else:
        img, data = iteritems(file).next()
        name = data['name']
        video_details, result = getVideoDetails(data['files'][0], img, bitbucket)
        inputFile = '-'
        file = '-'

    newfilePath = os.path.normpath(os.path.join(newDir, name) + core.VEXTENSION)

    map_cmd = []
    video_cmd = []
    audio_cmd = []
    audio_cmd2 = []
    sub_cmd = []
    meta_cmd = []
    other_cmd = []

    if not video_details or not video_details.get(
            "streams"):  # we couldn't read streams with ffprobe. Set defaults to try transcoding.
        videoStreams = []
        audioStreams = []
        subStreams = []

        map_cmd.extend(['-map', '0'])
        if core.VCODEC:
            video_cmd.extend(['-c:v', core.VCODEC])
            if core.VCODEC == 'libx264' and core.VPRESET:
                video_cmd.extend(['-pre', core.VPRESET])
        else:
            video_cmd.extend(['-c:v', 'copy'])
        if core.VFRAMERATE:
            video_cmd.extend(['-r', str(core.VFRAMERATE)])
        if core.VBITRATE:
            video_cmd.extend(['-b:v', str(core.VBITRATE)])
        if core.VRESOLUTION:
            video_cmd.extend(['-vf', 'scale={vres}'.format(vres=core.VRESOLUTION)])
        if core.VPRESET:
            video_cmd.extend(['-preset', core.VPRESET])
        if core.VCRF:
            video_cmd.extend(['-crf', str(core.VCRF)])
        if core.VLEVEL:
            video_cmd.extend(['-level', str(core.VLEVEL)])

        if core.ACODEC:
            audio_cmd.extend(['-c:a', core.ACODEC])
            if core.ACODEC in ['aac',
                               'dts']:  # Allow users to use the experimental AAC codec that's built into recent versions of ffmpeg
                audio_cmd.extend(['-strict', '-2'])
        else:
            audio_cmd.extend(['-c:a', 'copy'])
        if core.ACHANNELS:
            audio_cmd.extend(['-ac', str(core.ACHANNELS)])
        if core.ABITRATE:
            audio_cmd.extend(['-b:a', str(core.ABITRATE)])
        if core.OUTPUTQUALITYPERCENT:
            audio_cmd.extend(['-q:a', str(core.OUTPUTQUALITYPERCENT)])

        if core.SCODEC and core.ALLOWSUBS:
            sub_cmd.extend(['-c:s', core.SCODEC])
        elif core.ALLOWSUBS:  # Not every subtitle codec can be used for every video container format!
            sub_cmd.extend(['-c:s', 'copy'])
        else:  # http://en.wikibooks.org/wiki/FFMPEG_An_Intermediate_Guide/subtitle_options
            sub_cmd.extend(['-sn'])  # Don't copy the subtitles over

        if core.OUTPUTFASTSTART:
            other_cmd.extend(['-movflags', '+faststart'])

    else:
        videoStreams = [item for item in video_details["streams"] if item["codec_type"] == "video"]
        audioStreams = [item for item in video_details["streams"] if item["codec_type"] == "audio"]
        subStreams = [item for item in video_details["streams"] if item["codec_type"] == "subtitle"]
        if core.VEXTENSION not in ['.mkv', '.mpegts']:
            subStreams = [item for item in video_details["streams"] if
                          item["codec_type"] == "subtitle" and item["codec_name"] != "hdmv_pgs_subtitle" and item[
                              "codec_name"] != "pgssub"]

    for video in videoStreams:
        codec = video["codec_name"]
        fr = video.get("avg_frame_rate", 0)
        width = video.get("width", 0)
        height = video.get("height", 0)
        scale = core.VRESOLUTION
        if codec in core.VCODEC_ALLOW or not core.VCODEC:
            video_cmd.extend(['-c:v', 'copy'])
        else:
            video_cmd.extend(['-c:v', core.VCODEC])
        if core.VFRAMERATE and not (core.VFRAMERATE * 0.999 <= fr <= core.VFRAMERATE * 1.001):
            video_cmd.extend(['-r', str(core.VFRAMERATE)])
        if scale:
            w_scale = width / float(scale.split(':')[0])
            h_scale = height / float(scale.split(':')[1])
            if w_scale > h_scale:  # widescreen, Scale by width only.
                scale = "{width}:{height}".format(
                    width=scale.split(':')[0],
                    height=int((height / w_scale) / 2) * 2,
                )
                if w_scale > 1:
                    video_cmd.extend(['-vf', 'scale={width}'.format(width=scale)])
            else:  # lower or matching ratio, scale by height only.
                scale = "{width}:{height}".format(
                    width=int((width / h_scale) / 2) * 2,
                    height=scale.split(':')[1],
                )
                if h_scale > 1:
                    video_cmd.extend(['-vf', 'scale={height}'.format(height=scale)])
        if core.VBITRATE:
            video_cmd.extend(['-b:v', str(core.VBITRATE)])
        if core.VPRESET:
            video_cmd.extend(['-preset', core.VPRESET])
        if core.VCRF:
            video_cmd.extend(['-crf', str(core.VCRF)])
        if core.VLEVEL:
            video_cmd.extend(['-level', str(core.VLEVEL)])
        no_copy = ['-vf', '-r', '-crf', '-level', '-preset', '-b:v']
        if video_cmd[1] == 'copy' and any(i in video_cmd for i in no_copy):
            video_cmd[1] = core.VCODEC
        if core.VCODEC == 'copy':  # force copy. therefore ignore all other video transcoding.
            video_cmd = ['-c:v', 'copy']
        map_cmd.extend(['-map', '0:{index}'.format(index=video["index"])])
        break  # Only one video needed

    used_audio = 0
    a_mapped = []
    commentary = []
    if audioStreams:
        for i, val in reversed(list(enumerate(audioStreams))):
            try:
                if "Commentary" in val.get("tags").get("title"): # Split out commentry tracks.
                    commentary.append(val)
                    del audioStreams[i]
            except:
                continue
        try:
            audio1 = [item for item in audioStreams if item["tags"]["language"] == core.ALANGUAGE]
        except:  # no language tags. Assume only 1 language.
            audio1 = audioStreams
        try:
            audio2 = [item for item in audio1 if item["codec_name"] in core.ACODEC_ALLOW]
        except:
            audio2 = []
        try:
            audio3 = [item for item in audioStreams if item["tags"]["language"] != core.ALANGUAGE]
        except:
            audio3 = []
        try:
            audio4 = [item for item in audio3 if item["codec_name"] in core.ACODEC_ALLOW]
        except:
            audio4 = []

        if audio2:  # right (or only) language and codec...
            map_cmd.extend(['-map', '0:{index}'.format(index=audio2[0]["index"])])
            a_mapped.extend([audio2[0]["index"]])
            bitrate = int(float(audio2[0].get("bit_rate", 0))) / 1000
            channels = int(float(audio2[0].get("channels", 0)))
            audio_cmd.extend(['-c:a:{0}'.format(used_audio), 'copy'])
        elif audio1:  # right (or only) language, wrong codec.
            map_cmd.extend(['-map', '0:{index}'.format(index=audio1[0]["index"])])
            a_mapped.extend([audio1[0]["index"]])
            bitrate = int(float(audio1[0].get("bit_rate", 0))) / 1000
            channels = int(float(audio1[0].get("channels", 0)))
            audio_cmd.extend(['-c:a:{0}'.format(used_audio), core.ACODEC if core.ACODEC else 'copy'])
        elif audio4:  # wrong language, right codec.
            map_cmd.extend(['-map', '0:{index}'.format(index=audio4[0]["index"])])
            a_mapped.extend([audio4[0]["index"]])
            bitrate = int(float(audio4[0].get("bit_rate", 0))) / 1000
            channels = int(float(audio4[0].get("channels", 0)))
            audio_cmd.extend(['-c:a:{0}'.format(used_audio), 'copy'])
        elif audio3:  # wrong language, wrong codec. just pick the default audio track
            map_cmd.extend(['-map', '0:{index}'.format(index=audio3[0]["index"])])
            a_mapped.extend([audio3[0]["index"]])
            bitrate = int(float(audio3[0].get("bit_rate", 0))) / 1000
            channels = int(float(audio3[0].get("channels", 0)))
            audio_cmd.extend(['-c:a:{0}'.format(used_audio), core.ACODEC if core.ACODEC else 'copy'])

        if core.ACHANNELS and channels and channels > core.ACHANNELS:
            audio_cmd.extend(['-ac:a:{0}'.format(used_audio), str(core.ACHANNELS)])
            if audio_cmd[1] == 'copy':
                audio_cmd[1] = core.ACODEC
        if core.ABITRATE and not (core.ABITRATE * 0.9 < bitrate < core.ABITRATE * 1.1):
            audio_cmd.extend(['-b:a:{0}'.format(used_audio), str(core.ABITRATE)])
            if audio_cmd[1] == 'copy':
                audio_cmd[1] = core.ACODEC
        if core.OUTPUTQUALITYPERCENT:
            audio_cmd.extend(['-q:a:{0}'.format(used_audio), str(core.OUTPUTQUALITYPERCENT)])
            if audio_cmd[1] == 'copy':
                audio_cmd[1] = core.ACODEC
        if audio_cmd[1] in ['aac', 'dts']:
            audio_cmd[2:2] = ['-strict', '-2']

        if core.ACODEC2_ALLOW:
            used_audio += 1
            try:
                audio5 = [item for item in audio1 if item["codec_name"] in core.ACODEC2_ALLOW]
            except:
                audio5 = []
            try:
                audio6 = [item for item in audio3 if item["codec_name"] in core.ACODEC2_ALLOW]
            except:
                audio6 = []
            if audio5:  # right language and codec.
                map_cmd.extend(['-map', '0:{index}'.format(index=audio5[0]["index"])])
                a_mapped.extend([audio5[0]["index"]])
                bitrate = int(float(audio5[0].get("bit_rate", 0))) / 1000
                channels = int(float(audio5[0].get("channels", 0)))
                audio_cmd2.extend(['-c:a:{0}'.format(used_audio), 'copy'])
            elif audio1:  # right language wrong codec.
                map_cmd.extend(['-map', '0:{index}'.format(index=audio1[0]["index"])])
                a_mapped.extend([audio1[0]["index"]])
                bitrate = int(float(audio1[0].get("bit_rate", 0))) / 1000
                channels = int(float(audio1[0].get("channels", 0)))
                if core.ACODEC2:
                    audio_cmd2.extend(['-c:a:{0}'.format(used_audio), core.ACODEC2])
                else:
                    audio_cmd2.extend(['-c:a:{0}'.format(used_audio), 'copy'])
            elif audio6:  # wrong language, right codec
                map_cmd.extend(['-map', '0:{index}'.format(index=audio6[0]["index"])])
                a_mapped.extend([audio6[0]["index"]])
                bitrate = int(float(audio6[0].get("bit_rate", 0))) / 1000
                channels = int(float(audio6[0].get("channels", 0)))
                audio_cmd2.extend(['-c:a:{0}'.format(used_audio), 'copy'])
            elif audio3:  # wrong language, wrong codec just pick the default audio track
                map_cmd.extend(['-map', '0:{index}'.format(index=audio3[0]["index"])])
                a_mapped.extend([audio3[0]["index"]])
                bitrate = int(float(audio3[0].get("bit_rate", 0))) / 1000
                channels = int(float(audio3[0].get("channels", 0)))
                if core.ACODEC2:
                    audio_cmd2.extend(['-c:a:{0}'.format(used_audio), core.ACODEC2])
                else:
                    audio_cmd2.extend(['-c:a:{0}'.format(used_audio), 'copy'])

            if core.ACHANNELS2 and channels and channels > core.ACHANNELS2:
                audio_cmd2.extend(['-ac:a:{0}'.format(used_audio), str(core.ACHANNELS2)])
                if audio_cmd2[1] == 'copy':
                    audio_cmd2[1] = core.ACODEC2
            if core.ABITRATE2 and not (core.ABITRATE2 * 0.9 < bitrate < core.ABITRATE2 * 1.1):
                audio_cmd2.extend(['-b:a:{0}'.format(used_audio), str(core.ABITRATE2)])
                if audio_cmd2[1] == 'copy':
                    audio_cmd2[1] = core.ACODEC2
            if core.OUTPUTQUALITYPERCENT:
                audio_cmd2.extend(['-q:a:{0}'.format(used_audio), str(core.OUTPUTQUALITYPERCENT)])
                if audio_cmd2[1] == 'copy':
                    audio_cmd2[1] = core.ACODEC2
            if audio_cmd2[1] in ['aac', 'dts']:
                audio_cmd2[2:2] = ['-strict', '-2']

            if a_mapped[1] == a_mapped[0] and audio_cmd2[1:] == audio_cmd[1:]: #check for duplicate output track.
                del map_cmd[-2:]
            else:
                audio_cmd.extend(audio_cmd2)

        if core.AINCLUDE and core.ACODEC3:
            audioStreams.extend(commentary) #add commentry tracks back here.
            for audio in audioStreams:
                if audio["index"] in a_mapped:
                    continue
                used_audio += 1
                map_cmd.extend(['-map', '0:{index}'.format(index=audio["index"])])
                audio_cmd3 = []
                bitrate = int(float(audio.get("bit_rate", 0))) / 1000
                channels = int(float(audio.get("channels", 0)))
                if audio["codec_name"] in core.ACODEC3_ALLOW:
                    audio_cmd3.extend(['-c:a:{0}'.format(used_audio), 'copy'])
                else:
                    if core.ACODEC3:
                        audio_cmd3.extend(['-c:a:{0}'.format(used_audio), core.ACODEC3])
                    else:
                        audio_cmd3.extend(['-c:a:{0}'.format(used_audio), 'copy'])

                if core.ACHANNELS3 and channels and channels > core.ACHANNELS3:
                    audio_cmd3.extend(['-ac:a:{0}'.format(used_audio), str(core.ACHANNELS3)])
                    if audio_cmd3[1] == 'copy':
                        audio_cmd3[1] = core.ACODEC3
                if core.ABITRATE3 and not (core.ABITRATE3 * 0.9 < bitrate < core.ABITRATE3 * 1.1):
                    audio_cmd3.extend(['-b:a:{0}'.format(used_audio), str(core.ABITRATE3)])
                    if audio_cmd3[1] == 'copy':
                        audio_cmd3[1] = core.ACODEC3
                if core.OUTPUTQUALITYPERCENT > 0:
                    audio_cmd3.extend(['-q:a:{0}'.format(used_audio), str(core.OUTPUTQUALITYPERCENT)])
                    if audio_cmd3[1] == 'copy':
                        audio_cmd3[1] = core.ACODEC3
                if audio_cmd3[1] in ['aac', 'dts']:
                    audio_cmd3[2:2] = ['-strict', '-2']
                audio_cmd.extend(audio_cmd3)

    s_mapped = []
    burnt = 0
    n = 0
    for lan in core.SLANGUAGES:
        try:
            subs1 = [item for item in subStreams if item["tags"]["language"] == lan]
        except:
            subs1 = []
        if core.BURN and not subs1 and not burnt and os.path.isfile(file):
            for subfile in get_subs(file):
                if lan in os.path.split(subfile)[1]:
                    video_cmd.extend(['-vf', 'subtitles={subs}'.format(subs=subfile)])
                    burnt = 1
        for sub in subs1:
            if core.BURN and not burnt and os.path.isfile(inputFile):
                subloc = 0
                for index in range(len(subStreams)):
                    if subStreams[index]["index"] == sub["index"]:
                        subloc = index
                        break
                video_cmd.extend(['-vf', 'subtitles={sub}:si={loc}'.format(sub=inputFile, loc=subloc)])
                burnt = 1
            if not core.ALLOWSUBS:
                break
            if sub["codec_name"] in ["dvd_subtitle", "VobSub"] and core.SCODEC == "mov_text": # We can't convert these.
                continue
            map_cmd.extend(['-map', '0:{index}'.format(index=sub["index"])])
            s_mapped.extend([sub["index"]])

    if core.SINCLUDE:
        for sub in subStreams:
            if not core.ALLOWSUBS:
                break
            if sub["index"] in s_mapped:
                continue
            if sub["codec_name"] in ["dvd_subtitle", "VobSub"] and core.SCODEC == "mov_text": # We can't convert these.
                continue
            map_cmd.extend(['-map', '0:{index}'.format(index=sub["index"])])
            s_mapped.extend([sub["index"]])

    if core.OUTPUTFASTSTART:
        other_cmd.extend(['-movflags', '+faststart'])

    command = [core.FFMPEG, '-loglevel', 'warning']

    if core.HWACCEL:
        command.extend(['-hwaccel', 'auto'])
    if core.GENERALOPTS:
        command.extend(core.GENERALOPTS)

    command.extend(['-i', inputFile])

    if core.SEMBED and os.path.isfile(file):
        for subfile in get_subs(file):
            sub_details, result = getVideoDetails(subfile)
            if not sub_details or not sub_details.get("streams"):
                continue
            if core.SCODEC == "mov_text":
                subcode = [stream["codec_name"] for stream in sub_details["streams"]]
                if set(subcode).intersection(["dvd_subtitle", "VobSub"]): # We can't convert these.
                    continue
            command.extend(['-i', subfile])
            lan = os.path.splitext(os.path.splitext(subfile)[0])[1][1:].split('-')[0]
            metlan = None
            try:
                if len(lan) == 3:
                    metlan = Language(lan)
                if len(lan) == 2:
                    metlan = Language.fromalpha2(lan)
            except: pass
            if metlan:
                meta_cmd.extend(['-metadata:s:s:{x}'.format(x=len(s_mapped) + n),
                                 'language={lang}'.format(lang=metlan.alpha3)])
            n += 1
            map_cmd.extend(['-map', '{x}:0'.format(x=n)])

    if not core.ALLOWSUBS or (not s_mapped and not n):
        sub_cmd.extend(['-sn'])
    else:
        if core.SCODEC:
            sub_cmd.extend(['-c:s', core.SCODEC])
        else:
            sub_cmd.extend(['-c:s', 'copy'])

    command.extend(map_cmd)
    command.extend(video_cmd)
    command.extend(audio_cmd)
    command.extend(sub_cmd)
    command.extend(meta_cmd)
    command.extend(other_cmd)
    command.append(newfilePath)
    if platform.system() != 'Windows':
        command = core.NICENESS + command
    return command


def get_subs(file):
    filepaths = []
    subExt = ['.srt', '.sub', '.idx']
    name = os.path.splitext(os.path.split(file)[1])[0]
    dir = os.path.split(file)[0]
    for dirname, dirs, filenames in os.walk(dir):
        for filename in filenames:
            filepaths.extend([os.path.join(dirname, filename)])
    subfiles = [item for item in filepaths if os.path.splitext(item)[1] in subExt and name in item]
    return subfiles


def extract_subs(file, newfilePath, bitbucket):
    video_details, result = getVideoDetails(file)
    if not video_details:
        return

    if core.SUBSDIR:
        subdir = core.SUBSDIR
    else:
        subdir = os.path.split(newfilePath)[0]
    name = os.path.splitext(os.path.split(newfilePath)[1])[0]

    try:
        subStreams = [item for item in video_details["streams"] if
                      item["codec_type"] == "subtitle" and item["tags"]["language"] in core.SLANGUAGES and item[
                          "codec_name"] != "hdmv_pgs_subtitle" and item["codec_name"] != "pgssub"]
    except:
        subStreams = [item for item in video_details["streams"] if
                      item["codec_type"] == "subtitle" and item["codec_name"] != "hdmv_pgs_subtitle" and item[
                          "codec_name"] != "pgssub"]
    num = len(subStreams)
    for n in range(num):
        sub = subStreams[n]
        idx = sub["index"]
        lan = sub.get("tags", {}).get("language", "unk")

        if num == 1:
            outputFile = os.path.join(subdir, "{0}.srt".format(name))
            if os.path.isfile(outputFile):
                outputFile = os.path.join(subdir, "{0}.{1}.srt".format(name, n))
        else:
            outputFile = os.path.join(subdir, "{0}.{1}.srt".format(name, lan))
            if os.path.isfile(outputFile):
                outputFile = os.path.join(subdir, "{0}.{1}.{2}.srt".format(name, lan, n))

        command = [core.FFMPEG, '-loglevel', 'warning', '-i', file, '-vn', '-an',
                   '-codec:{index}'.format(index=idx), 'srt', outputFile]
        if platform.system() != 'Windows':
            command = core.NICENESS + command

        logger.info("Extracting {0} subtitle from: {1}".format(lan, file))
        print_cmd(command)
        result = 1  # set result to failed in case call fails.
        try:
            proc = subprocess.Popen(command, stdout=bitbucket, stderr=bitbucket)
            proc.communicate()
            result = proc.returncode
        except:
            logger.error("Extracting subtitle has failed")

        if result == 0:
            try:
                shutil.copymode(file, outputFile)
            except:
                pass
            logger.info("Extracting {0} subtitle from {1} has succeeded".format(lan, file))
        else:
            logger.error("Extracting subtitles has failed")


def processList(List, newDir, bitbucket):
    remList = []
    newList = []
    combine = []
    vtsPath = None
    success = True
    for item in List:
        ext = os.path.splitext(item)[1].lower()
        if ext in ['.iso', '.bin', '.img'] and ext not in core.IGNOREEXTENSIONS:
            logger.debug("Attempting to rip disk image: {0}".format(item), "TRANSCODER")
            newList.extend(ripISO(item, newDir, bitbucket))
            remList.append(item)
        elif re.match(".+VTS_[0-9][0-9]_[0-9].[Vv][Oo][Bb]", item) and '.vob' not in core.IGNOREEXTENSIONS:
            logger.debug("Found VIDEO_TS image file: {0}".format(item), "TRANSCODER")
            if not vtsPath:
                try:
                    vtsPath = re.match("(.+VIDEO_TS)", item).groups()[0]
                except:
                    vtsPath = os.path.split(item)[0]
            remList.append(item)
        elif re.match(".+VIDEO_TS.", item) or re.match(".+VTS_[0-9][0-9]_[0-9].", item):
            remList.append(item)
        elif core.CONCAT and re.match(".+[cC][dD][0-9].", item):
            remList.append(item)
            combine.append(item)
        else:
            continue
    if vtsPath:
        newList.extend(combineVTS(vtsPath))
    if combine:
        newList.extend(combineCD(combine))
    for file in newList:
        if isinstance(file, basestring) and 'concat:' not in file and not os.path.isfile(file):
            success = False
            break
    if success and newList:
        List.extend(newList)
        for item in remList:
            List.remove(item)
        logger.debug("Successfully extracted .vob file {0} from disk image".format(newList[0]), "TRANSCODER")
    elif newList and not success:
        newList = []
        remList = []
        logger.error("Failed extracting .vob files from disk image. Stopping transcoding.", "TRANSCODER")
    return List, remList, newList, success


def ripISO(item, newDir, bitbucket):
    newFiles = []
    failure_dir = 'failure'
    # Mount the ISO in your OS and call combineVTS.
    if not core.SEVENZIP:
        logger.error("No 7zip installed. Can't extract image file {0}".format(item), "TRANSCODER")
        newFiles = [failure_dir]
        return newFiles
    cmd = [core.SEVENZIP, 'l', item]
    try:
        logger.debug("Attempting to extract .vob from image file {0}".format(item), "TRANSCODER")
        print_cmd(cmd)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=bitbucket)
        out, err = proc.communicate()
        fileList = [re.match(".+(VIDEO_TS[\\\/]VTS_[0-9][0-9]_[0-9].[Vv][Oo][Bb])", line).groups()[0] for line in
                    out.splitlines() if re.match(".+VIDEO_TS[\\\/]VTS_[0-9][0-9]_[0-9].[Vv][Oo][Bb]", line)]
        combined = []
        for n in range(99):
            concat = []
            m = 1
            while True:
                vtsName = 'VIDEO_TS{0}VTS_{1:02d}_{2:d}.VOB'.format(os.sep, n + 1, m)
                if vtsName in fileList:
                    concat.append(vtsName)
                    m += 1
                else:
                    break
            if not concat:
                break
            if core.CONCAT:
                combined.extend(concat)
                continue
            name = '{name}.cd{x}'.format(
                name=os.path.splitext(os.path.split(item)[1])[0], x=n + 1
            )
            newFiles.append({item: {'name': name, 'files': concat}})
        if core.CONCAT:
            name = os.path.splitext(os.path.split(item)[1])[0]
            newFiles.append({item: {'name': name, 'files': combined}})
        if not newFiles:
            logger.error("No VIDEO_TS folder found in image file {0}".format(item), "TRANSCODER")
            newFiles = [failure_dir]
    except:
        logger.error("Failed to extract from image file {0}".format(item), "TRANSCODER")
        newFiles = [failure_dir]
    return newFiles


def combineVTS(vtsPath):
    newFiles = []
    combined = ''
    for n in range(99):
        concat = ''
        m = 1
        while True:
            vtsName = 'VTS_{0:02d}_{1:d}.VOB'.format(n + 1, m)
            if os.path.isfile(os.path.join(vtsPath, vtsName)):
                concat += '{file}|'.format(file=os.path.join(vtsPath, vtsName))
                m += 1
            else:
                break
        if not concat:
            break
        if core.CONCAT:
            combined += '{files}|'.format(files=concat)
            continue
        newFiles.append('concat:{0}'.format(concat[:-1]))
    if core.CONCAT:
        newFiles.append('concat:{0}'.format(combined[:-1]))
    return newFiles


def combineCD(combine):
    newFiles = []
    for item in set([re.match("(.+)[cC][dD][0-9].", item).groups()[0] for item in combine]):
        concat = ''
        for n in range(99):
            files = [file for file in combine if
                     n + 1 == int(re.match(".+[cC][dD]([0-9]+).", file).groups()[0]) and item in file]
            if files:
                concat += '{file}|'.format(file=files[0])
            else:
                break
        if concat:
            newFiles.append('concat:{0}'.format(concat[:-1]))
    return newFiles


def print_cmd(command):
    cmd = ""
    for item in command:
        cmd = "{cmd} {item}".format(cmd=cmd, item=item)
    logger.debug("calling command:{0}".format(cmd))


def Transcode_directory(dirName):
    if not core.FFMPEG:
        return 1, dirName
    logger.info("Checking for files to be transcoded")
    final_result = 0  # initialize as successful
    if core.OUTPUTVIDEOPATH:
        newDir = core.OUTPUTVIDEOPATH
        makeDir(newDir)
        name = os.path.splitext(os.path.split(dirName)[1])[0]
        newDir = os.path.join(newDir, name)
        makeDir(newDir)
    else:
        newDir = dirName
    if platform.system() == 'Windows':
        bitbucket = open('NUL')
    else:
        bitbucket = open('/dev/null')
    movieName = os.path.splitext(os.path.split(dirName)[1])[0]
    List = core.listMediaFiles(dirName, media=True, audio=False, meta=False, archives=False)
    List, remList, newList, success = processList(List, newDir, bitbucket)
    if not success:
        bitbucket.close()
        return 1, dirName

    for file in List:
        if isinstance(file, basestring) and os.path.splitext(file)[1] in core.IGNOREEXTENSIONS:
            continue
        command = buildCommands(file, newDir, movieName, bitbucket)
        newfilePath = command[-1]

        # transcoding files may remove the original file, so make sure to extract subtitles first
        if core.SEXTRACT and isinstance(file, basestring):
            extract_subs(file, newfilePath, bitbucket)

        try:  # Try to remove the file that we're transcoding to just in case. (ffmpeg will return an error if it already exists for some reason)
            os.remove(newfilePath)
        except OSError as e:
            if e.errno != errno.ENOENT:  # Ignore the error if it's just telling us that the file doesn't exist
                logger.debug("Error when removing transcoding target: {0}".format(e))
        except Exception as e:
            logger.debug("Error when removing transcoding target: {0}".format(e))

        logger.info("Transcoding video: {0}".format(newfilePath))
        print_cmd(command)
        result = 1  # set result to failed in case call fails.
        try:
            if isinstance(file, basestring):
                proc = subprocess.Popen(command, stdout=bitbucket, stderr=bitbucket)
            else:
                img, data = iteritems(file).next()
                proc = subprocess.Popen(command, stdout=bitbucket, stderr=bitbucket, stdin=subprocess.PIPE)
                for vob in data['files']:
                    procin = zip_out(vob, img, bitbucket)
                    if procin:
                        shutil.copyfileobj(procin.stdout, proc.stdin)
                        procin.stdout.close()
            proc.communicate()
            result = proc.returncode
        except:
            logger.error("Transcoding of video {0} has failed".format(newfilePath))

        if core.SUBSDIR and result == 0 and isinstance(file, basestring):
            for sub in get_subs(file):
                name = os.path.splitext(os.path.split(file)[1])[0]
                subname = os.path.split(sub)[1]
                newname = os.path.splitext(os.path.split(newfilePath)[1])[0]
                newpath = os.path.join(core.SUBSDIR, subname.replace(name, newname))
                if not os.path.isfile(newpath):
                    os.rename(sub, newpath)

        if result == 0:
            try:
                shutil.copymode(file, newfilePath)
            except:
                pass
            logger.info("Transcoding of video to {0} succeeded".format(newfilePath))
            if os.path.isfile(newfilePath) and (file in newList or not core.DUPLICATE):
                try:
                    os.unlink(file)
                except:
                    pass
        else:
            logger.error("Transcoding of video to {0} failed with result {1}".format(newfilePath, result))
        # this will be 0 (successful) it all are successful, else will return a positive integer for failure.
        final_result = final_result + result
    if final_result == 0 and not core.DUPLICATE:
        for file in remList:
            try:
                os.unlink(file)
            except:
                pass
    if not os.listdir(unicode(newDir)):  # this is an empty directory and we didn't transcode into it.
        os.rmdir(newDir)
        newDir = dirName
    if not core.PROCESSOUTPUT and core.DUPLICATE:  # We postprocess the original files to CP/SB 
        newDir = dirName
    bitbucket.close()
    return final_result, newDir
