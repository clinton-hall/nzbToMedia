# pylint: disable=too-many-lines
from __future__ import annotations

import errno
import json
import logging
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import time
from subprocess import DEVNULL
from subprocess import PIPE

from babelfish import Language

import nzb2media
from nzb2media.utils.files import list_media_files
from nzb2media.utils.paths import make_dir

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

MOUNTED = None
GETSUBS = False
TRANSCODE = None
CONCAT = None
DUPLICATE = None
IGNOREEXTENSIONS = []
VEXTENSION = None
OUTPUTVIDEOPATH = None
PROCESSOUTPUT = False
GENERALOPTS: list[str] = []
OTHEROPTS: list[str] = []
ALANGUAGE = None
AINCLUDE = False
SLANGUAGES: list[str] = []
SINCLUDE = False
SUBSDIR = None
ALLOWSUBS = False
SEXTRACT = False
SEMBED = False
BURN = False
DEFAULTS = None
VCODEC = None
VCODEC_ALLOW = []
VPRESET = None
VFRAMERATE = None
VBITRATE = None
VLEVEL = None
VCRF = None
VRESOLUTION = None
ACODEC = None
ACODEC_ALLOW = []
ACHANNELS = None
ABITRATE = None
ACODEC2 = None
ACODEC2_ALLOW: list[str] = []
ACHANNELS2 = None
ABITRATE2 = None
ACODEC3 = None
ACODEC3_ALLOW = []
ACHANNELS3 = None
ABITRATE3 = None
SCODEC = None
OUTPUTFASTSTART = None
OUTPUTQUALITYPERCENT = None
HWACCEL = False


def is_video_good(video: pathlib.Path, status, require_lan=None):
    file_ext = video.suffix
    disable = False
    if file_ext not in nzb2media.MEDIA_CONTAINER or not nzb2media.tool.FFPROBE or not nzb2media.CHECK_MEDIA or file_ext in {'.iso'} or (status > 0 and nzb2media.NOEXTRACTFAILED):
        disable = True
    else:
        test_details, res = get_video_details(nzb2media.TEST_FILE)
        if res or test_details.get('error'):
            disable = True
            log.info('DISABLED: ffprobe failed to analyse test file. Stopping corruption check.')
        if test_details.get('streams'):
            vid_streams = [item for item in test_details['streams'] if 'codec_type' in item and item['codec_type'] == 'video']
            aud_streams = [item for item in test_details['streams'] if 'codec_type' in item and item['codec_type'] == 'audio']
            if not (len(vid_streams) > 0 and len(aud_streams) > 0):
                disable = True
                log.info('DISABLED: ffprobe failed to analyse streams from test file. Stopping corruption check.')
    if disable:
        if status:
            # if the download was 'failed', assume bad.
            # If it was successful, assume good.
            return False
        return True
    log.info(f'Checking [{video.name}] for corruption, please stand by ...')
    video_details, result = get_video_details(video)
    if result:
        log.error(f'FAILED: [{video.name}] is corrupted!')
        return False
    if video_details.get('error'):
        error_details = video_details.get('error')
        log.info(f'FAILED: [{video.name}] returned error [{error_details}].')
        return False
    if video_details.get('streams'):
        video_streams = [item for item in video_details['streams'] if item['codec_type'] == 'video']
        audio_streams = [item for item in video_details['streams'] if item['codec_type'] == 'audio']
        if require_lan:
            valid_audio = [item for item in audio_streams if 'tags' in item and 'language' in item['tags'] and item['tags']['language'] in require_lan]
        else:
            valid_audio = audio_streams
        if len(video_streams) > 0 and len(valid_audio) > 0:
            log.info(f'SUCCESS: [{video.name}] has no corruption.')
            return True
        log.info(f'FAILED: [{video.name}] has {len(video_streams)} video streams and {len(audio_streams)} audio streams. Assume corruption.')
        return False


def zip_out(file, img):
    if os.path.isfile(file):
        cmd = ['cat', file]
    else:
        cmd = [os.fspath(nzb2media.tool.SEVENZIP), '-so', 'e', img, file]
    try:
        with subprocess.Popen(cmd, stdout=PIPE, stderr=DEVNULL) as proc:
            return proc
    except Exception:
        log.error(f'Extracting [{file}] has failed')
        return None


def get_video_details(videofile, img=None):
    video_details = {}
    result = 1
    file = videofile
    if not nzb2media.tool.FFPROBE:
        return video_details, result
    print_format = '-of' if 'avprobe' in nzb2media.tool.FFPROBE.name else '-print_format'
    try:
        if img:
            videofile = '-'
        command = [os.fspath(nzb2media.tool.FFPROBE), '-v', 'quiet', print_format, 'json', '-show_format', '-show_streams', '-show_error', videofile]
        print_cmd(command)
        if img:
            procin = zip_out(file, img)
            with subprocess.Popen(command, stdout=PIPE, stdin=procin.stdout) as proc:
                proc_out, proc_err = proc.communicate()
                result = proc.returncode
            procin.stdout.close()
        else:
            with subprocess.Popen(command, stdout=PIPE) as proc:
                proc_out, proc_err = proc.communicate()
                result = proc.returncode
        video_details = json.loads(proc_out.decode())
    except Exception:
        try:  # try this again without -show error in case of ffmpeg limitation
            command = [os.fspath(nzb2media.tool.FFPROBE), '-v', 'quiet', print_format, 'json', '-show_format', '-show_streams', videofile]
            print_cmd(command)
            if img:
                procin = zip_out(file, img)
                with subprocess.Popen(command, stdout=PIPE, stdin=procin.stdout) as proc:
                    proc_out, proc_err = proc.communicate()
                    result = proc.returncode
                procin.stdout.close()
            else:
                with subprocess.Popen(command, stdout=PIPE) as proc:
                    proc_out, proc_err = proc.communicate()
                    result = proc.returncode
            video_details = json.loads(proc_out.decode())
        except Exception:
            log.error(f'Checking [{file}] has failed')
    return video_details, result


def check_vid_file(video_details, result):
    if result:
        return False
    if video_details.get('error'):
        return False
    if not video_details.get('streams'):
        return False
    video_streams = [item for item in video_details['streams'] if item['codec_type'] == 'video']
    audio_streams = [item for item in video_details['streams'] if item['codec_type'] == 'audio']
    if len(video_streams) > 0 and len(audio_streams) > 0:
        return True
    return False


def build_commands(file, new_dir, movie_name):
    global VEXTENSION
    if isinstance(file, str):
        input_file = file
        if 'concat:' in file:
            file = file.split('|')[0].replace('concat:', '')
        video_details, result = get_video_details(file)
        directory, name = os.path.split(file)
        name, ext = os.path.splitext(name)
        check = re.match('VTS_([0-9][0-9])_[0-9]+', name)
        if check and CONCAT:
            name = movie_name
        elif check:
            name = f'{movie_name}.cd{check.groups()[0]}'
        elif CONCAT and re.match('(.+)[cC][dD][0-9]', name):
            name = re.sub('([ ._=:-]+[cC][dD][0-9])', '', name)
        if ext == VEXTENSION and new_dir == directory:  # we need to change the name to prevent overwriting itself.
            VEXTENSION = f'-transcoded{VEXTENSION}'  # adds '-transcoded.ext'
        new_file = file
    else:
        img, data = next(file.items())
        name = data['name']
        new_file = []
        rem_vid = []
        for vid in data['files']:
            video_details, result = get_video_details(vid, img)
            if not check_vid_file(video_details, result):
                # lets not transcode menu or other clips that don't have audio and video.
                rem_vid.append(vid)
        data['files'] = [f for f in data['files'] if f not in rem_vid]
        new_file = {img: {'name': data['name'], 'files': data['files']}}
        video_details, result = get_video_details(data['files'][0], img)
        input_file = '-'
        file = '-'
    newfile_path = os.path.normpath(os.path.join(new_dir, name) + VEXTENSION)
    map_cmd = []
    video_cmd = []
    audio_cmd = []
    audio_cmd2 = []
    sub_cmd = []
    meta_cmd = []
    other_cmd = []
    if not video_details or not video_details.get('streams'):
        # we couldn't read streams with ffprobe. Set defaults to try transcoding.
        video_streams = []
        audio_streams = []
        sub_streams = []
        map_cmd.extend(['-map', '0'])
        if VCODEC:
            video_cmd.extend(['-c:v', VCODEC])
            if VCODEC == 'libx264' and VPRESET:
                video_cmd.extend(['-pre', VPRESET])
        else:
            video_cmd.extend(['-c:v', 'copy'])
        if VFRAMERATE:
            video_cmd.extend(['-r', str(VFRAMERATE)])
        if VBITRATE:
            video_cmd.extend(['-b:v', str(VBITRATE)])
        if VRESOLUTION:
            video_cmd.extend(['-vf', f'scale={VRESOLUTION}'])
        if VPRESET:
            video_cmd.extend(['-preset', VPRESET])
        if VCRF:
            video_cmd.extend(['-crf', str(VCRF)])
        if VLEVEL:
            video_cmd.extend(['-level', str(VLEVEL)])
        if ACODEC:
            audio_cmd.extend(['-c:a', ACODEC])
            if ACODEC in {'aac', 'dts'}:
                # Allow users to use the experimental AAC codec that's built into recent versions of ffmpeg
                audio_cmd.extend(['-strict', '-2'])
        else:
            audio_cmd.extend(['-c:a', 'copy'])
        if ACHANNELS:
            audio_cmd.extend(['-ac', str(ACHANNELS)])
        if ABITRATE:
            audio_cmd.extend(['-b:a', str(ABITRATE)])
        if OUTPUTQUALITYPERCENT:
            audio_cmd.extend(['-q:a', str(OUTPUTQUALITYPERCENT)])
        if SCODEC and ALLOWSUBS:
            sub_cmd.extend(['-c:s', SCODEC])
        elif ALLOWSUBS:  # Not every subtitle codec can be used for every video container format!
            sub_cmd.extend(['-c:s', 'copy'])
        else:  # http://en.wikibooks.org/wiki/FFMPEG_An_Intermediate_Guide/subtitle_options
            sub_cmd.extend(['-sn'])  # Don't copy the subtitles over
        if OUTPUTFASTSTART:
            other_cmd.extend(['-movflags', '+faststart'])
    else:
        video_streams = [item for item in video_details['streams'] if item['codec_type'] == 'video']
        audio_streams = [item for item in video_details['streams'] if item['codec_type'] == 'audio']
        sub_streams = [item for item in video_details['streams'] if item['codec_type'] == 'subtitle']
        if VEXTENSION not in ['.mkv', '.mpegts']:
            sub_streams = [item for item in video_details['streams'] if item['codec_type'] == 'subtitle' and item['codec_name'] != 'hdmv_pgs_subtitle' and item['codec_name'] != 'pgssub']
    for video in video_streams:
        codec = video['codec_name']
        frame_rate = video.get('avg_frame_rate', 0)
        width = video.get('width', 0)
        height = video.get('height', 0)
        scale = VRESOLUTION
        if codec in VCODEC_ALLOW or not VCODEC:
            video_cmd.extend(['-c:v', 'copy'])
        else:
            video_cmd.extend(['-c:v', VCODEC])
        if VFRAMERATE and not VFRAMERATE * 0.999 <= frame_rate <= VFRAMERATE * 1.001:
            video_cmd.extend(['-r', str(VFRAMERATE)])
        if scale:
            w_scale = width / float(scale.split(':')[0])
            h_scale = height / float(scale.split(':')[1])
            if w_scale > h_scale:  # widescreen, Scale by width only.
                _width = scale.split(':')[0]
                _height = int((height / w_scale) / 2) * 2
                scale = f'{_width}:{_height}'
                if w_scale > 1:
                    video_cmd.extend(['-vf', f'scale={scale}'])
            else:  # lower or matching ratio, scale by height only.
                _width = int((width / h_scale) / 2) * 2
                _height = scale.split(':')[1]
                scale = f'{_width}:{_height}'
                if h_scale > 1:
                    video_cmd.extend(['-vf', f'scale={scale}'])
        if VBITRATE:
            video_cmd.extend(['-b:v', str(VBITRATE)])
        if VPRESET:
            video_cmd.extend(['-preset', VPRESET])
        if VCRF:
            video_cmd.extend(['-crf', str(VCRF)])
        if VLEVEL:
            video_cmd.extend(['-level', str(VLEVEL)])
        no_copy = ['-vf', '-r', '-crf', '-level', '-preset', '-b:v']
        if video_cmd[1] == 'copy' and any(i in video_cmd for i in no_copy):
            video_cmd[1] = VCODEC
        if VCODEC == 'copy':  # force copy. therefore ignore all other video transcoding.
            video_cmd = ['-c:v', 'copy']
        _index = video['index']
        map_cmd.extend(['-map', f'0:{_index}'])
        break  # Only one video needed
    used_audio = 0
    a_mapped = []
    commentary = []
    if audio_streams:
        for i, val in reversed(list(enumerate(audio_streams))):
            try:
                if 'Commentary' in val.get('tags').get('title'):
                    # Split out commentry tracks.
                    commentary.append(val)
                    del audio_streams[i]
            except Exception:
                continue
        try:
            audio1 = [item for item in audio_streams if item['tags']['language'] == ALANGUAGE]
        except Exception:  # no language tags. Assume only 1 language.
            audio1 = audio_streams
        try:
            audio2 = [item for item in audio1 if item['codec_name'] in ACODEC_ALLOW]
        except Exception:
            audio2 = []
        try:
            audio3 = [item for item in audio_streams if item['tags']['language'] != ALANGUAGE]
        except Exception:
            audio3 = []
        try:
            audio4 = [item for item in audio3 if item['codec_name'] in ACODEC_ALLOW]
        except Exception:
            audio4 = []
        if audio2:  # right (or only) language and codec...
            _index = audio2[0]['index']
            map_cmd.extend(['-map', f'0:{_index}'])
            a_mapped.extend([audio2[0]['index']])
            bitrate = int(float(audio2[0].get('bit_rate', 0))) / 1000
            channels = int(float(audio2[0].get('channels', 0)))
            audio_cmd.extend([f'-c:a:{used_audio}', 'copy'])
        elif audio1:  # right (or only) language, wrong codec.
            _index = audio1[0]['index']
            map_cmd.extend(['-map', f'0:{_index}'])
            a_mapped.extend([audio1[0]['index']])
            bitrate = int(float(audio1[0].get('bit_rate', 0))) / 1000
            channels = int(float(audio1[0].get('channels', 0)))
            audio_cmd.extend([f'-c:a:{used_audio}', ACODEC if ACODEC else 'copy'])
        elif audio4:
            # wrong language, right codec.
            _index = audio4[0]['index']
            map_cmd.extend(['-map', f'0:{_index}'])
            a_mapped.extend([audio4[0]['index']])
            bitrate = int(float(audio4[0].get('bit_rate', 0))) / 1000
            channels = int(float(audio4[0].get('channels', 0)))
            audio_cmd.extend([f'-c:a:{used_audio}', 'copy'])
        elif audio3:
            # wrong language, wrong codec. just pick the default audio track
            _index = audio3[0]['index']
            map_cmd.extend(['-map', f'0:{_index}'])
            a_mapped.extend([audio3[0]['index']])
            bitrate = int(float(audio3[0].get('bit_rate', 0))) / 1000
            channels = int(float(audio3[0].get('channels', 0)))
            audio_cmd.extend([f'-c:a:{used_audio}', ACODEC if ACODEC else 'copy'])
        if ACHANNELS and channels and channels > ACHANNELS:
            audio_cmd.extend([f'-ac:a:{used_audio}', str(ACHANNELS)])
            if audio_cmd[1] == 'copy':
                audio_cmd[1] = ACODEC
        if ABITRATE and not ABITRATE * 0.9 < bitrate < ABITRATE * 1.1:
            audio_cmd.extend([f'-b:a:{used_audio}', str(ABITRATE)])
            if audio_cmd[1] == 'copy':
                audio_cmd[1] = ACODEC
        if OUTPUTQUALITYPERCENT:
            audio_cmd.extend([f'-q:a:{used_audio}', str(OUTPUTQUALITYPERCENT)])
            if audio_cmd[1] == 'copy':
                audio_cmd[1] = ACODEC
        if audio_cmd[1] in {'aac', 'dts'}:
            audio_cmd[2:2] = ['-strict', '-2']
        if ACODEC2_ALLOW:
            used_audio += 1
            try:
                audio5 = [item for item in audio1 if item['codec_name'] in ACODEC2_ALLOW]
            except Exception:
                audio5 = []
            try:
                audio6 = [item for item in audio3 if item['codec_name'] in ACODEC2_ALLOW]
            except Exception:
                audio6 = []
            if audio5:  # right language and codec.
                _index = audio5[0]['index']
                map_cmd.extend(['-map', f'0:{_index}'])
                a_mapped.extend([audio5[0]['index']])
                bitrate = int(float(audio5[0].get('bit_rate', 0))) / 1000
                channels = int(float(audio5[0].get('channels', 0)))
                audio_cmd2.extend([f'-c:a:{used_audio}', 'copy'])
            elif audio1:  # right language wrong codec.
                _index = audio1[0]['index']
                map_cmd.extend(['-map', f'0:{_index}'])
                a_mapped.extend([audio1[0]['index']])
                bitrate = int(float(audio1[0].get('bit_rate', 0))) / 1000
                channels = int(float(audio1[0].get('channels', 0)))
                if ACODEC2:
                    audio_cmd2.extend([f'-c:a:{used_audio}', ACODEC2])
                else:
                    audio_cmd2.extend([f'-c:a:{used_audio}', 'copy'])
            elif audio6:  # wrong language, right codec
                _index = audio6[0]['index']
                map_cmd.extend(['-map', f'0:{_index}'])
                a_mapped.extend([audio6[0]['index']])
                bitrate = int(float(audio6[0].get('bit_rate', 0))) / 1000
                channels = int(float(audio6[0].get('channels', 0)))
                audio_cmd2.extend([f'-c:a:{used_audio}', 'copy'])
            elif audio3:
                # wrong language, wrong codec just pick the default audio track
                _index = audio3[0]['index']
                map_cmd.extend(['-map', f'0:{_index}'])
                a_mapped.extend([audio3[0]['index']])
                bitrate = int(float(audio3[0].get('bit_rate', 0))) / 1000
                channels = int(float(audio3[0].get('channels', 0)))
                if ACODEC2:
                    audio_cmd2.extend([f'-c:a:{used_audio}', ACODEC2])
                else:
                    audio_cmd2.extend([f'-c:a:{used_audio}', 'copy'])
            if ACHANNELS2 and channels and channels > ACHANNELS2:
                audio_cmd2.extend([f'-ac:a:{used_audio}', str(ACHANNELS2)])
                if audio_cmd2[1] == 'copy':
                    audio_cmd2[1] = ACODEC2
            if ABITRATE2 and not ABITRATE2 * 0.9 < bitrate < ABITRATE2 * 1.1:
                audio_cmd2.extend([f'-b:a:{used_audio}', str(ABITRATE2)])
                if audio_cmd2[1] == 'copy':
                    audio_cmd2[1] = ACODEC2
            if OUTPUTQUALITYPERCENT:
                audio_cmd2.extend([f'-q:a:{used_audio}', str(OUTPUTQUALITYPERCENT)])
                if audio_cmd2[1] == 'copy':
                    audio_cmd2[1] = ACODEC2
            if audio_cmd2[1] in {'aac', 'dts'}:
                audio_cmd2[2:2] = ['-strict', '-2']
            if a_mapped[1] == a_mapped[0] and audio_cmd2[1:] == audio_cmd[1:]:
                # check for duplicate output track.
                del map_cmd[-2:]
            else:
                audio_cmd.extend(audio_cmd2)
        if AINCLUDE and ACODEC3:
            # add commentary tracks back here.
            audio_streams.extend(commentary)
            for audio in audio_streams:
                if audio['index'] in a_mapped:
                    continue
                used_audio += 1
                _index = audio['index']
                map_cmd.extend(['-map', f'0:{_index}'])
                audio_cmd3 = []
                bitrate = int(float(audio.get('bit_rate', 0))) / 1000
                channels = int(float(audio.get('channels', 0)))
                if audio['codec_name'] in ACODEC3_ALLOW:
                    audio_cmd3.extend([f'-c:a:{used_audio}', 'copy'])
                elif ACODEC3:
                    audio_cmd3.extend([f'-c:a:{used_audio}', ACODEC3])
                else:
                    audio_cmd3.extend([f'-c:a:{used_audio}', 'copy'])
                if ACHANNELS3 and channels and channels > ACHANNELS3:
                    audio_cmd3.extend([f'-ac:a:{used_audio}', str(ACHANNELS3)])
                    if audio_cmd3[1] == 'copy':
                        audio_cmd3[1] = ACODEC3
                if ABITRATE3 and not ABITRATE3 * 0.9 < bitrate < ABITRATE3 * 1.1:
                    audio_cmd3.extend([f'-b:a:{used_audio}', str(ABITRATE3)])
                    if audio_cmd3[1] == 'copy':
                        audio_cmd3[1] = ACODEC3
                if OUTPUTQUALITYPERCENT > 0:
                    audio_cmd3.extend([f'-q:a:{used_audio}', str(OUTPUTQUALITYPERCENT)])
                    if audio_cmd3[1] == 'copy':
                        audio_cmd3[1] = ACODEC3
                if audio_cmd3[1] in {'aac', 'dts'}:
                    audio_cmd3[2:2] = ['-strict', '-2']
                audio_cmd.extend(audio_cmd3)
    s_mapped = []
    burnt = 0
    num = 0
    for lan in SLANGUAGES:
        try:
            subs1 = [item for item in sub_streams if item['tags']['language'] == lan]
        except Exception:
            subs1 = []
        if BURN and not subs1 and not burnt and os.path.isfile(file):
            for subfile in get_subs(file):
                if lan in os.path.split(subfile)[1]:
                    video_cmd.extend(['-vf', f'subtitles={subfile}'])
                    burnt = 1
        for sub in subs1:
            if BURN and not burnt and os.path.isfile(input_file):
                subloc = 0
                for index, sub_stream in enumerate(sub_streams):
                    if sub_stream['index'] == sub['index']:
                        subloc = index
                        break
                video_cmd.extend(['-vf', f'subtitles={input_file}:si={subloc}'])
                burnt = 1
            if not ALLOWSUBS:
                break
            if sub['codec_name'] in {'dvd_subtitle', 'VobSub'} and SCODEC == 'mov_text':
                continue  # We can't convert these.
            _index = sub['index']
            map_cmd.extend(['-map', f'0:{_index}'])
            s_mapped.extend([sub['index']])
    if SINCLUDE:
        for sub in sub_streams:
            if not ALLOWSUBS:
                break
            if sub['index'] in s_mapped:
                continue
            if sub['codec_name'] in {'dvd_subtitle', 'VobSub'} and SCODEC == 'mov_text':  # We can't convert these.
                continue
            _index = sub['index']
            map_cmd.extend(['-map', f'0:{_index}'])
            s_mapped.extend([sub['index']])
    if OUTPUTFASTSTART:
        other_cmd.extend(['-movflags', '+faststart'])
    if OTHEROPTS:
        other_cmd.extend(OTHEROPTS)
    command = [nzb2media.tool.FFMPEG, '-loglevel', 'warning']
    if HWACCEL:
        command.extend(['-hwaccel', 'auto'])
    if GENERALOPTS:
        command.extend(GENERALOPTS)
    command.extend(['-i', input_file])
    if SEMBED and os.path.isfile(file):
        for subfile in get_subs(file):
            sub_details, result = get_video_details(subfile)
            if not sub_details or not sub_details.get('streams'):
                continue
            if SCODEC == 'mov_text':
                subcode = [stream['codec_name'] for stream in sub_details['streams']]
                if set(subcode).intersection(['dvd_subtitle', 'VobSub']):
                    # We can't convert these.
                    continue
            command.extend(['-i', subfile])
            lan = os.path.splitext(os.path.splitext(subfile)[0])[1][1:].split('-')[0]
            metlan = None
            try:
                if len(lan) == 3:
                    metlan = Language(lan)
                if len(lan) == 2:
                    metlan = Language.fromalpha2(lan)
            except Exception:
                pass
            if metlan:
                meta_cmd.extend([f'-metadata:s:s:{len(s_mapped) + num}', f'language={metlan.alpha3}'])
            num += 1
            map_cmd.extend(['-map', f'{num}:0'])
    if not ALLOWSUBS or (not s_mapped and not num):
        sub_cmd.extend(['-sn'])
    elif SCODEC:
        sub_cmd.extend(['-c:s', SCODEC])
    else:
        sub_cmd.extend(['-c:s', 'copy'])
    command.extend(map_cmd)
    command.extend(video_cmd)
    command.extend(audio_cmd)
    command.extend(sub_cmd)
    command.extend(meta_cmd)
    command.extend(other_cmd)
    command.append(newfile_path)
    if platform.system() != 'Windows':
        command = nzb2media.tool.NICENESS + command
    return command, new_file


def get_subs(file):
    filepaths = []
    sub_ext = ['.srt', '.sub', '.idx']
    name = os.path.splitext(os.path.split(file)[1])[0]
    path = os.path.split(file)[0]
    for directory, _, filenames in os.walk(path):
        for filename in filenames:
            filepaths.extend([os.path.join(directory, filename)])
    subfiles = [item for item in filepaths if os.path.splitext(item)[1] in sub_ext and name in item]
    return subfiles


def extract_subs(file, newfile_path):
    video_details, result = get_video_details(file)
    if not video_details:
        return
    if SUBSDIR:
        subdir = SUBSDIR
    else:
        subdir = os.path.split(newfile_path)[0]
    name = os.path.splitext(os.path.split(newfile_path)[1])[0]
    try:
        sub_streams = [item for item in video_details['streams'] if item['codec_type'] == 'subtitle' and item['tags']['language'] in SLANGUAGES and item['codec_name'] != 'hdmv_pgs_subtitle' and item['codec_name'] != 'pgssub']
    except Exception:
        sub_streams = [item for item in video_details['streams'] if item['codec_type'] == 'subtitle' and item['codec_name'] != 'hdmv_pgs_subtitle' and item['codec_name'] != 'pgssub']
    num = len(sub_streams)
    for ea_num in range(num):
        sub = sub_streams[ea_num]
        idx = sub['index']
        lan = sub.get('tags', {}).get('language', 'unk')
        if num == 1:
            output_file = os.path.join(subdir, f'{name}.srt')
            if os.path.isfile(output_file):
                output_file = os.path.join(subdir, f'{name}.{ea_num}.srt')
        else:
            output_file = os.path.join(subdir, f'{name}.{lan}.srt')
            if os.path.isfile(output_file):
                output_file = os.path.join(subdir, f'{name}.{lan}.{ea_num}.srt')
        command = [nzb2media.tool.FFMPEG, '-loglevel', 'warning', '-i', file, '-vn', '-an', f'-codec:{idx}', 'srt', output_file]
        if platform.system() != 'Windows':
            command = nzb2media.tool.NICENESS + command
        log.info(f'Extracting {lan} subtitle from: {file}')
        print_cmd(command)
        result = 1  # set result to failed in case call fails.
        try:
            with subprocess.Popen(command, stdout=DEVNULL, stderr=DEVNULL) as proc:
                proc_out, proc_error = proc.communicate()
                result = proc.returncode
        except Exception:
            log.error('Extracting subtitle has failed')
        if not result:
            try:
                shutil.copymode(file, output_file)
            except Exception:
                pass
            log.info(f'Extracting {lan} subtitle from {file} has succeeded')
        else:
            log.error('Extracting subtitles has failed')


def process_list(iterable):
    rem_list = []
    new_list = []
    combine = []
    vts_path = None
    mts_path = None
    success = True
    for item in iterable:
        ext = os.path.splitext(item)[1].lower()
        if ext in {'.iso', '.bin', '.img'} and ext not in IGNOREEXTENSIONS:
            log.debug(f'Attempting to rip disk image: {item}')
            new_list.extend(rip_iso(item))
            rem_list.append(item)
        elif re.match('.+VTS_[0-9][0-9]_[0-9].[Vv][Oo][Bb]', item) and '.vob' not in IGNOREEXTENSIONS:
            log.debug(f'Found VIDEO_TS image file: {item}')
            if not vts_path:
                try:
                    vts_path = re.match('(.+VIDEO_TS)', item).groups()[0]
                except Exception:
                    vts_path = os.path.split(item)[0]
            rem_list.append(item)
        elif re.match('.+BDMV[/\\]SOURCE[/\\][0-9]+[0-9].[Mm][Tt][Ss]', item) and '.mts' not in IGNOREEXTENSIONS:
            log.debug(f'Found MTS image file: {item}')
            if not mts_path:
                try:
                    mts_path = re.match('(.+BDMV[/\\]SOURCE)', item).groups()[0]
                except Exception:
                    mts_path = os.path.split(item)[0]
            rem_list.append(item)
        elif re.match('.+VIDEO_TS.', item) or re.match('.+VTS_[0-9][0-9]_[0-9].', item):
            rem_list.append(item)
        elif CONCAT and re.match('.+[cC][dD][0-9].', item):
            rem_list.append(item)
            combine.append(item)
        else:
            continue
    if vts_path:
        new_list.extend(combine_vts(vts_path))
    if mts_path:
        new_list.extend(combine_mts(mts_path))
    if combine:
        new_list.extend(combine_cd(combine))
    for file in new_list:
        if isinstance(file, str) and 'concat:' not in file and not os.path.isfile(file):
            success = False
            break
    if success and new_list:
        iterable.extend(new_list)
        for item in rem_list:
            iterable.remove(item)
        log.debug(f'Successfully extracted .vob file {new_list[0]} from disk image')
    elif new_list and not success:
        new_list = []
        rem_list = []
        log.error('Failed extracting .vob files from disk image. Stopping transcoding.')
    return iterable, rem_list, new_list, success


def mount_iso(item):  # Currently only supports Linux Mount when permissions allow.
    global MOUNTED
    if platform.system() == 'Windows':
        log.error(f'No mounting options available under Windows for image file {item}')
        return []
    mount_point = os.path.join(os.path.dirname(os.path.abspath(item)), 'temp')
    make_dir(mount_point)
    cmd = ['mount', '-o', 'loop', item, mount_point]
    print_cmd(cmd)
    with subprocess.Popen(cmd, stdout=PIPE, stderr=DEVNULL) as proc:
        proc_out, proc_err = proc.communicate()
    MOUNTED = mount_point  # Allows us to verify this has been done and then cleanup.
    for root, _dirs, files in os.walk(mount_point):
        for file in files:
            full_path = os.path.join(root, file)
            if re.match('.+VTS_[0-9][0-9]_[0-9].[Vv][Oo][Bb]', full_path) and '.vob' not in IGNOREEXTENSIONS:
                log.debug(f'Found VIDEO_TS image file: {full_path}')
                try:
                    vts_path = re.match('(.+VIDEO_TS)', full_path).groups()[0]
                except Exception:
                    vts_path = os.path.split(full_path)[0]
                return combine_vts(vts_path)
            if re.match('.+BDMV[/\\]STREAM[/\\][0-9]+[0-9].[Mm]', full_path) and '.mts' not in IGNOREEXTENSIONS:
                log.debug(f'Found MTS image file: {full_path}')
                try:
                    mts_path = re.match('(.+BDMV[/\\]STREAM)', full_path).groups()[0]
                except Exception:
                    mts_path = os.path.split(full_path)[0]
                return combine_mts(mts_path)
    log.error(f'No VIDEO_TS or BDMV/SOURCE folder found in image file {mount_point}')
    return ['failure']  # If we got here, nothing matched our criteria


def rip_iso(item):
    new_files = []
    failure_dir = 'failure'
    # Mount the ISO in your OS and call combineVTS.
    if not nzb2media.tool.SEVENZIP:
        log.debug(f'No 7zip installed. Attempting to mount image file {item}')
        try:
            # Currently only works for Linux.
            new_files = mount_iso(item)
        except Exception:
            log.error(f'Failed to mount and extract from image file {item}')
            new_files = [failure_dir]
        return new_files
    cmd = [nzb2media.tool.SEVENZIP, 'l', item]
    try:
        log.debug(f'Attempting to extract .vob or .mts from image file {item}')
        print_cmd(cmd)
        with subprocess.Popen(cmd, stdout=PIPE, stderr=DEVNULL) as proc:
            proc_out, proc_err = proc.communicate()
        file_match_gen = (re.match(r'.+(VIDEO_TS[/\\]VTS_[0-9][0-9]_[0-9].[Vv][Oo][Bb])', line) for line in proc_out.decode().splitlines())
        file_list = [file_match.groups()[0] for file_match in file_match_gen if file_match]
        combined = []
        if file_list:  # handle DVD
            for title_set in range(99):
                concat = []
                part = 1
                while True:
                    vts_name = f'VIDEO_TS{os.sep}VTS_{title_set + 1:02d}_{part:d}.VOB'
                    if vts_name in file_list:
                        concat.append(vts_name)
                        part += 1
                    else:
                        break
                if not concat:
                    break
                if CONCAT:
                    combined.extend(concat)
                    continue
                name = f'{os.path.splitext(os.path.split(item)[1])[0]}.cd{title_set + 1}'
                new_files.append({item: {'name': name, 'files': concat}})
        else:
            # check BlueRay for BDMV/STREAM/XXXX.MTS
            mts_list_gen = (re.match(r'.+(BDMV[/\\]STREAM[/\\][0-9]+[0-9].[Mm]).', line) for line in proc_out.decode().splitlines())
            mts_list = [file_match.groups()[0] for file_match in mts_list_gen if file_match]
            mts_list.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
            title_set = 0
            for mts_name in mts_list:
                concat = []
                title_set += 1
                concat.append(mts_name)
                if CONCAT:
                    combined.extend(concat)
                    continue
                name = f'{os.path.splitext(os.path.split(item)[1])[0]}.cd{title_set}'
                new_files.append({item: {'name': name, 'files': concat}})
        if CONCAT and combined:
            name = os.path.splitext(os.path.split(item)[1])[0]
            new_files.append({item: {'name': name, 'files': combined}})
        if not new_files:
            log.error(f'No VIDEO_TS or BDMV/SOURCE folder found in image file. Attempting to mount and scan {item}')
            new_files = mount_iso(item)
    except Exception:
        log.error(f'Failed to extract from image file {item}')
        new_files = [failure_dir]
    return new_files


def combine_vts(vts_path):
    new_files = []
    combined = []
    name = re.match(r'(.+)[/\\]VIDEO_TS', vts_path).groups()[0]
    if os.path.basename(name) == 'temp':
        name = os.path.basename(os.path.dirname(name))
    else:
        name = os.path.basename(name)
    for title_set in range(99):
        concat = []
        part = 1
        while True:
            vts_name = f'VTS_{title_set + 1:02d}_{part:d}.VOB'
            if os.path.isfile(os.path.join(vts_path, vts_name)):
                concat.append(os.path.join(vts_path, vts_name))
                part += 1
            else:
                break
        if not concat:
            break
        if CONCAT:
            combined.extend(concat)
            continue
        name = f'{name}.cd{title_set + 1}'
        new_files.append({vts_path: {'name': name, 'files': concat}})
    if CONCAT:
        new_files.append({vts_path: {'name': name, 'files': combined}})
    return new_files


def combine_mts(mts_path):
    new_files = []
    combined = []
    name = re.match(r'(.+)[/\\]BDMV[/\\]STREAM', mts_path).groups()[0]
    if os.path.basename(name) == 'temp':
        name = os.path.basename(os.path.dirname(name))
    else:
        name = os.path.basename(name)
    num = 0
    mts_list = [f for f in os.listdir(mts_path) if os.path.isfile(os.path.join(mts_path, f))]
    if sys.version_info[0] == 2:  # Python2 sorting
        mts_list.sort(key=lambda f: int(filter(str.isdigit, f)))
    else:  # Python3 sorting
        mts_list.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
    for mts_name in mts_list:  # need to sort all files [1 - 998].mts in order
        concat = []
        concat.append(os.path.join(mts_path, mts_name))
        if CONCAT:
            combined.extend(concat)
            continue
        name = f'{name}.cd{num + 1}'
        new_files.append({mts_path: {'name': name, 'files': concat}})
        num += 1
    if CONCAT:
        new_files.append({mts_path: {'name': name, 'files': combined}})
    return new_files


def combine_cd(combine):
    new_files = []
    for item in {re.match('(.+)[cC][dD][0-9].', ea_item).groups()[0] for ea_item in combine}:
        concat = ''
        for num in range(99):
            files = [file for file in combine if num + 1 == int(re.match('.+[cC][dD]([0-9]+).', file).groups()[0]) and item in file]
            if files:
                concat += f'{files[0]}|'
            else:
                break
        if concat:
            new_files.append(f'concat:{concat[:-1]}')
    return new_files


def print_cmd(command):
    cmd = ''
    for item in command:
        cmd = f'{cmd} {item}'
    log.debug(f'calling command:{cmd}')


def transcode_directory(dir_name):
    global MOUNTED
    if not nzb2media.tool.FFMPEG:
        return 1, dir_name
    log.info('Checking for files to be transcoded')
    final_result = 0  # initialize as successful
    if OUTPUTVIDEOPATH:
        new_dir = OUTPUTVIDEOPATH
        make_dir(new_dir)
        name = os.path.splitext(os.path.split(dir_name)[1])[0]
        new_dir = os.path.join(new_dir, name)
        make_dir(new_dir)
    else:
        new_dir = dir_name
    movie_name = os.path.splitext(os.path.split(dir_name)[1])[0]
    file_list = list_media_files(dir_name, media=True, audio=False, meta=False, archives=False)
    file_list, rem_list, new_list, success = process_list(file_list)
    if not success:
        return 1, dir_name
    for file in file_list:
        if isinstance(file, str) and os.path.splitext(file)[1] in IGNOREEXTENSIONS:
            continue
        command, file = build_commands(file, new_dir, movie_name)
        newfile_path = command[-1]
        # transcoding files may remove the original file, so make sure to extract subtitles first
        if SEXTRACT and isinstance(file, str):
            extract_subs(file, newfile_path)
        try:  # Try to remove the file that we're transcoding to just in case. (ffmpeg will return an error if it already exists for some reason)
            os.remove(newfile_path)
        except OSError as error:
            if error.errno != errno.ENOENT:  # Ignore the error if it's just telling us that the file doesn't exist
                log.debug(f'Error when removing transcoding target: {error}')
        except Exception as error:
            log.debug(f'Error when removing transcoding target: {error}')
        log.info(f'Transcoding video: {newfile_path}')
        print_cmd(command)
        result = 1  # set result to failed in case call fails.
        try:
            if isinstance(file, str):
                with subprocess.Popen(command, stdout=DEVNULL, stderr=PIPE) as proc:
                    out, err = proc.communicate()
            else:
                img, data = next(file.items())
                with subprocess.Popen(command, stdout=DEVNULL, stderr=PIPE, stdin=PIPE) as proc:
                    for vob in data['files']:
                        procin = zip_out(vob, img)
                        if procin:
                            log.debug(f'Feeding in file: {vob} to Transcoder')
                            shutil.copyfileobj(procin.stdout, proc.stdin)
                            procin.stdout.close()
                    out, err = proc.communicate()
            if err:
                log.error(f'Transcoder returned:{err} has failed')
            result = proc.returncode
        except Exception:
            log.error(f'Transcoding of video {newfile_path} has failed')
        if SUBSDIR and not result and isinstance(file, str):
            for sub in get_subs(file):
                name = os.path.splitext(os.path.split(file)[1])[0]
                subname = os.path.split(sub)[1]
                newname = os.path.splitext(os.path.split(newfile_path)[1])[0]
                newpath = os.path.join(SUBSDIR, subname.replace(name, newname))
                if not os.path.isfile(newpath):
                    os.rename(sub, newpath)
        if not result:
            try:
                shutil.copymode(file, newfile_path)
            except Exception:
                pass
            log.info(f'Transcoding of video to {newfile_path} succeeded')
            if os.path.isfile(newfile_path) and (file in new_list or not DUPLICATE):
                try:
                    os.unlink(file)
                except Exception:
                    pass
        else:
            log.error(f'Transcoding of video to {newfile_path} failed with result {result}')
        # this will be 0 (successful) it all are successful, else will return a positive integer for failure.
        final_result = final_result + result
    if MOUNTED:  # In case we mounted an .iso file, unmount here.
        time.sleep(5)  # play it safe and avoid failing to unmount.
        cmd = ['umount', '-l', MOUNTED]
        print_cmd(cmd)
        with subprocess.Popen(cmd, stdout=PIPE, stderr=DEVNULL) as proc:
            proc_out, proc_err = proc.communicate()
        time.sleep(5)
        os.rmdir(MOUNTED)
        MOUNTED = None
    if not final_result and not DUPLICATE:
        for file in rem_list:
            try:
                os.unlink(file)
            except Exception:
                pass
    if not os.listdir(new_dir):
        # this is an empty directory and we didn't transcode into it.
        os.rmdir(new_dir)
        new_dir = dir_name
    if not PROCESSOUTPUT and DUPLICATE:
        # We postprocess the original files to CP/SB
        new_dir = dir_name
    return final_result, new_dir


def configure_transcoder():
    global MOUNTED
    global GETSUBS
    global TRANSCODE
    global DUPLICATE
    global CONCAT
    global IGNOREEXTENSIONS
    global OUTPUTFASTSTART
    global GENERALOPTS
    global OTHEROPTS
    global OUTPUTQUALITYPERCENT
    global OUTPUTVIDEOPATH
    global PROCESSOUTPUT
    global ALANGUAGE
    global AINCLUDE
    global SLANGUAGES
    global SINCLUDE
    global SEXTRACT
    global SEMBED
    global SUBSDIR
    global VEXTENSION
    global VCODEC
    global VPRESET
    global VFRAMERATE
    global VBITRATE
    global VRESOLUTION
    global VCRF
    global VLEVEL
    global VCODEC_ALLOW
    global ACODEC
    global ACODEC_ALLOW
    global ACHANNELS
    global ABITRATE
    global ACODEC2
    global ACODEC2_ALLOW
    global ACHANNELS2
    global ABITRATE2
    global ACODEC3
    global ACODEC3_ALLOW
    global ACHANNELS3
    global ABITRATE3
    global SCODEC
    global BURN
    global HWACCEL
    global ALLOWSUBS
    global DEFAULTS
    MOUNTED = None
    GETSUBS = int(nzb2media.CFG['Transcoder']['getSubs'])
    TRANSCODE = int(nzb2media.CFG['Transcoder']['transcode'])
    DUPLICATE = int(nzb2media.CFG['Transcoder']['duplicate'])
    CONCAT = int(nzb2media.CFG['Transcoder']['concat'])
    IGNOREEXTENSIONS = nzb2media.CFG['Transcoder']['ignoreExtensions']
    if isinstance(IGNOREEXTENSIONS, str):
        IGNOREEXTENSIONS = IGNOREEXTENSIONS.split(',')
    OUTPUTFASTSTART = int(nzb2media.CFG['Transcoder']['outputFastStart'])
    GENERALOPTS = nzb2media.CFG['Transcoder']['generalOptions']
    if isinstance(GENERALOPTS, str):
        GENERALOPTS = GENERALOPTS.split(',')
    if GENERALOPTS == ['']:
        GENERALOPTS = []
    if '-fflags' not in GENERALOPTS:
        GENERALOPTS.append('-fflags')
    if '+genpts' not in GENERALOPTS:
        GENERALOPTS.append('+genpts')
    OTHEROPTS = nzb2media.CFG['Transcoder']['otherOptions']
    if isinstance(OTHEROPTS, str):
        OTHEROPTS = OTHEROPTS.split(',')
    if OTHEROPTS == ['']:
        OTHEROPTS = []
    try:
        OUTPUTQUALITYPERCENT = int(nzb2media.CFG['Transcoder']['outputQualityPercent'])
    except Exception:
        pass
    OUTPUTVIDEOPATH = nzb2media.CFG['Transcoder']['outputVideoPath']
    PROCESSOUTPUT = int(nzb2media.CFG['Transcoder']['processOutput'])
    ALANGUAGE = nzb2media.CFG['Transcoder']['audioLanguage']
    AINCLUDE = int(nzb2media.CFG['Transcoder']['allAudioLanguages'])
    SLANGUAGES = nzb2media.CFG['Transcoder']['subLanguages']
    if isinstance(SLANGUAGES, str):
        SLANGUAGES = SLANGUAGES.split(',')
    if SLANGUAGES == ['']:
        SLANGUAGES = []
    SINCLUDE = int(nzb2media.CFG['Transcoder']['allSubLanguages'])
    SEXTRACT = int(nzb2media.CFG['Transcoder']['extractSubs'])
    SEMBED = int(nzb2media.CFG['Transcoder']['embedSubs'])
    SUBSDIR = nzb2media.CFG['Transcoder']['externalSubDir']
    VEXTENSION = nzb2media.CFG['Transcoder']['outputVideoExtension'].strip()
    VCODEC = nzb2media.CFG['Transcoder']['outputVideoCodec'].strip()
    VCODEC_ALLOW = nzb2media.CFG['Transcoder']['VideoCodecAllow'].strip()
    if isinstance(VCODEC_ALLOW, str):
        VCODEC_ALLOW = VCODEC_ALLOW.split(',')
    if VCODEC_ALLOW == ['']:
        VCODEC_ALLOW = []
    VPRESET = nzb2media.CFG['Transcoder']['outputVideoPreset'].strip()
    try:
        VFRAMERATE = float(nzb2media.CFG['Transcoder']['outputVideoFramerate'].strip())
    except Exception:
        pass
    try:
        VCRF = int(nzb2media.CFG['Transcoder']['outputVideoCRF'].strip())
    except Exception:
        pass
    try:
        VLEVEL = nzb2media.CFG['Transcoder']['outputVideoLevel'].strip()
    except Exception:
        pass
    try:
        VBITRATE = int((nzb2media.CFG['Transcoder']['outputVideoBitrate'].strip()).replace('k', '000'))
    except Exception:
        pass
    VRESOLUTION = nzb2media.CFG['Transcoder']['outputVideoResolution']
    ACODEC = nzb2media.CFG['Transcoder']['outputAudioCodec'].strip()
    ACODEC_ALLOW = nzb2media.CFG['Transcoder']['AudioCodecAllow'].strip()
    if isinstance(ACODEC_ALLOW, str):
        ACODEC_ALLOW = ACODEC_ALLOW.split(',')
    if ACODEC_ALLOW == ['']:
        ACODEC_ALLOW = []
    try:
        ACHANNELS = int(nzb2media.CFG['Transcoder']['outputAudioChannels'].strip())
    except Exception:
        pass
    try:
        ABITRATE = int((nzb2media.CFG['Transcoder']['outputAudioBitrate'].strip()).replace('k', '000'))
    except Exception:
        pass
    ACODEC2 = nzb2media.CFG['Transcoder']['outputAudioTrack2Codec'].strip()
    ACODEC2_ALLOW = nzb2media.CFG['Transcoder']['AudioCodec2Allow'].strip()
    if isinstance(ACODEC2_ALLOW, str):
        ACODEC2_ALLOW = ACODEC2_ALLOW.split(',')
    if ACODEC2_ALLOW == ['']:
        ACODEC2_ALLOW = []
    try:
        ACHANNELS2 = int(nzb2media.CFG['Transcoder']['outputAudioTrack2Channels'].strip())
    except Exception:
        pass
    try:
        ABITRATE2 = int((nzb2media.CFG['Transcoder']['outputAudioTrack2Bitrate'].strip()).replace('k', '000'))
    except Exception:
        pass
    ACODEC3 = nzb2media.CFG['Transcoder']['outputAudioOtherCodec'].strip()
    ACODEC3_ALLOW = nzb2media.CFG['Transcoder']['AudioOtherCodecAllow'].strip()
    if isinstance(ACODEC3_ALLOW, str):
        ACODEC3_ALLOW = ACODEC3_ALLOW.split(',')
    if ACODEC3_ALLOW == ['']:
        ACODEC3_ALLOW = []
    try:
        ACHANNELS3 = int(nzb2media.CFG['Transcoder']['outputAudioOtherChannels'].strip())
    except Exception:
        pass
    try:
        ABITRATE3 = int((nzb2media.CFG['Transcoder']['outputAudioOtherBitrate'].strip()).replace('k', '000'))
    except Exception:
        pass
    SCODEC = nzb2media.CFG['Transcoder']['outputSubtitleCodec'].strip()
    BURN = int(nzb2media.CFG['Transcoder']['burnInSubtitle'].strip())
    DEFAULTS = nzb2media.CFG['Transcoder']['outputDefault'].strip()
    HWACCEL = int(nzb2media.CFG['Transcoder']['hwAccel'])
    allow_subs = ['.mkv', '.mp4', '.m4v', 'asf', 'wma', 'wmv']
    codec_alias = {'libx264': ['libx264', 'h264', 'h.264', 'AVC', 'MPEG-4'], 'libmp3lame': ['libmp3lame', 'mp3'], 'libfaac': ['libfaac', 'aac', 'faac']}
    transcode_defaults = {
        'iPad': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': None, 'ACHANNELS': 2, 'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
        'iPad-1080p': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': '1920:1080', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': None, 'ACHANNELS': 2, 'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
        'iPad-720p': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': '1280:720', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': None, 'ACHANNELS': 2, 'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
        'Apple-TV': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': '1280:720', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'ac3', 'ACODEC_ALLOW': ['ac3'], 'ABITRATE': None, 'ACHANNELS': 6, 'ACODEC2': 'aac', 'ACODEC2_ALLOW': ['libfaac'], 'ABITRATE2': None, 'ACHANNELS2': 2, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
        'iPod': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': '1280:720', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2, 'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
        'iPhone': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': '460:320', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2, 'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
        'PS3': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'ac3', 'ACODEC_ALLOW': ['ac3'], 'ABITRATE': None, 'ACHANNELS': 6, 'ACODEC2': 'aac', 'ACODEC2_ALLOW': ['libfaac'], 'ABITRATE2': None, 'ACHANNELS2': 2, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
        'xbox': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'ac3', 'ACODEC_ALLOW': ['ac3'], 'ABITRATE': None, 'ACHANNELS': 6, 'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
        'Roku-480p': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2, 'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
        'Roku-720p': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2, 'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
        'Roku-1080p': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 160000, 'ACHANNELS': 2, 'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
        'mkv': {'VEXTENSION': '.mkv', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4', 'mpeg2video'], 'ACODEC': 'dts', 'ACODEC_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE': None, 'ACHANNELS': 8, 'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None, 'ACODEC3': 'ac3', 'ACODEC3_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE3': None, 'ACHANNELS3': 8, 'SCODEC': 'mov_text'},
        'mkv-bluray': {'VEXTENSION': '.mkv', 'VCODEC': 'libx265', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'hevc', 'h265', 'libx265', 'h.265', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4', 'mpeg2video'], 'ACODEC': 'dts', 'ACODEC_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE': None, 'ACHANNELS': 8, 'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None, 'ACODEC3': 'ac3', 'ACODEC3_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE3': None, 'ACHANNELS3': 8, 'SCODEC': 'mov_text'},
        'mp4-scene-release': {'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': 19, 'VLEVEL': '3.1', 'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4', 'mpeg2video'], 'ACODEC': 'dts', 'ACODEC_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE': None, 'ACHANNELS': 8, 'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None, 'ACODEC3': 'ac3', 'ACODEC3_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE3': None, 'ACHANNELS3': 8, 'SCODEC': 'mov_text'},
        'MKV-SD': {'VEXTENSION': '.mkv', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': '1200k', 'VCRF': None, 'VLEVEL': None, 'VRESOLUTION': '720: -1', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'], 'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2, 'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6, 'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None, 'SCODEC': 'mov_text'},
    }
    if DEFAULTS and DEFAULTS in transcode_defaults:
        VEXTENSION = transcode_defaults[DEFAULTS]['VEXTENSION']
        VCODEC = transcode_defaults[DEFAULTS]['VCODEC']
        VPRESET = transcode_defaults[DEFAULTS]['VPRESET']
        VFRAMERATE = transcode_defaults[DEFAULTS]['VFRAMERATE']
        VBITRATE = transcode_defaults[DEFAULTS]['VBITRATE']
        VRESOLUTION = transcode_defaults[DEFAULTS]['VRESOLUTION']
        VCRF = transcode_defaults[DEFAULTS]['VCRF']
        VLEVEL = transcode_defaults[DEFAULTS]['VLEVEL']
        VCODEC_ALLOW = transcode_defaults[DEFAULTS]['VCODEC_ALLOW']
        ACODEC = transcode_defaults[DEFAULTS]['ACODEC']
        ACODEC_ALLOW = transcode_defaults[DEFAULTS]['ACODEC_ALLOW']
        ACHANNELS = transcode_defaults[DEFAULTS]['ACHANNELS']
        ABITRATE = transcode_defaults[DEFAULTS]['ABITRATE']
        ACODEC2 = transcode_defaults[DEFAULTS]['ACODEC2']
        ACODEC2_ALLOW = transcode_defaults[DEFAULTS]['ACODEC2_ALLOW']
        ACHANNELS2 = transcode_defaults[DEFAULTS]['ACHANNELS2']
        ABITRATE2 = transcode_defaults[DEFAULTS]['ABITRATE2']
        ACODEC3 = transcode_defaults[DEFAULTS]['ACODEC3']
        ACODEC3_ALLOW = transcode_defaults[DEFAULTS]['ACODEC3_ALLOW']
        ACHANNELS3 = transcode_defaults[DEFAULTS]['ACHANNELS3']
        ABITRATE3 = transcode_defaults[DEFAULTS]['ABITRATE3']
        SCODEC = transcode_defaults[DEFAULTS]['SCODEC']
    del transcode_defaults
    if VEXTENSION in allow_subs:
        ALLOWSUBS = 1
    if not VCODEC_ALLOW and VCODEC:
        VCODEC_ALLOW.extend([VCODEC])
    for codec in VCODEC_ALLOW:
        if codec in codec_alias:
            extra = [item for item in codec_alias[codec] if item not in VCODEC_ALLOW]
            VCODEC_ALLOW.extend(extra)
    if not ACODEC_ALLOW and ACODEC:
        ACODEC_ALLOW.extend([ACODEC])
    for codec in ACODEC_ALLOW:
        if codec in codec_alias:
            extra = [item for item in codec_alias[codec] if item not in ACODEC_ALLOW]
            ACODEC_ALLOW.extend(extra)
    if not ACODEC2_ALLOW and ACODEC2:
        ACODEC2_ALLOW.extend([ACODEC2])
    for codec in ACODEC2_ALLOW:
        if codec in codec_alias:
            extra = [item for item in codec_alias[codec] if item not in ACODEC2_ALLOW]
            ACODEC2_ALLOW.extend(extra)
    if not ACODEC3_ALLOW and ACODEC3:
        ACODEC3_ALLOW.extend([ACODEC3])
    for codec in ACODEC3_ALLOW:
        if codec in codec_alias:
            extra = [item for item in codec_alias[codec] if item not in ACODEC3_ALLOW]
            ACODEC3_ALLOW.extend(extra)
