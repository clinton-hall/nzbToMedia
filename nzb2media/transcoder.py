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

from babelfish import Language

import nzb2media
from nzb2media.utils.paths import make_dir

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

__author__ = 'Justin'


def is_video_good(video: pathlib.Path, status, require_lan=None):
    file_ext = video.suffix
    disable = False
    if (
        file_ext not in nzb2media.MEDIA_CONTAINER
        or not nzb2media.FFPROBE
        or not nzb2media.CHECK_MEDIA
        or file_ext in ['.iso']
        or (status > 0 and nzb2media.NOEXTRACTFAILED)
    ):
        disable = True
    else:
        test_details, res = get_video_details(nzb2media.TEST_FILE)
        if res != 0 or test_details.get('error'):
            disable = True
            log.info('DISABLED: ffprobe failed to analyse test file. Stopping corruption check.')
        if test_details.get('streams'):
            vid_streams = [
                item
                for item in test_details['streams']
                if 'codec_type' in item and item['codec_type'] == 'video'
            ]
            aud_streams = [
                item
                for item in test_details['streams']
                if 'codec_type' in item and item['codec_type'] == 'audio'
            ]
            if not (len(vid_streams) > 0 and len(aud_streams) > 0):
                disable = True
                log.info('DISABLED: ffprobe failed to analyse streams from test file. Stopping corruption check.')
    if disable:
        if status:
            # if the download was 'failed', assume bad.
            # If it was successful, assume good.
            return False
        else:
            return True

    log.info(f'Checking [{video.name}] for corruption, please stand by ...')
    video_details, result = get_video_details(video)

    if result != 0:
        log.error(f'FAILED: [{video.name}] is corrupted!')
        return False
    if video_details.get('error'):
        error_details = video_details.get('error')
        log.info(f'FAILED: [{video.name}] returned error [{error_details}].')
        return False
    if video_details.get('streams'):
        video_streams = [
            item
            for item in video_details['streams']
            if item['codec_type'] == 'video'
        ]
        audio_streams = [
            item
            for item in video_details['streams']
            if item['codec_type'] == 'audio'
        ]
        if require_lan:
            valid_audio = [
                item
                for item in audio_streams
                if 'tags' in item
                and 'language' in item['tags']
                and item['tags']['language'] in require_lan
            ]
        else:
            valid_audio = audio_streams
        if len(video_streams) > 0 and len(valid_audio) > 0:
            log.info(f'SUCCESS: [{video.name}] has no corruption.')
            return True
        else:
            log.info(f'FAILED: [{video.name}] has {len(video_streams)} video streams and {len(audio_streams)} audio streams. Assume corruption.')
            return False


def zip_out(file, img, bitbucket):
    procin = None
    if os.path.isfile(file):
        cmd = ['cat', file]
    else:
        cmd = [nzb2media.SEVENZIP, '-so', 'e', img, file]
    try:
        procin = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=bitbucket,
        )
    except Exception:
        log.error(f'Extracting [{file}] has failed')
    return procin


def get_video_details(videofile, img=None, bitbucket=None):
    video_details = {}
    result = 1
    file = videofile
    if not nzb2media.FFPROBE:
        return video_details, result
    print_format = '-of' if 'avprobe' in nzb2media.FFPROBE else '-print_format'
    try:
        if img:
            videofile = '-'
        command = [
            nzb2media.FFPROBE,
            '-v',
            'quiet',
            print_format,
            'json',
            '-show_format',
            '-show_streams',
            '-show_error',
            videofile,
        ]
        print_cmd(command)
        if img:
            procin = zip_out(file, img, bitbucket)
            proc = subprocess.Popen(
                command, stdout=subprocess.PIPE, stdin=procin.stdout,
            )
            procin.stdout.close()
        else:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE)
        out, err = proc.communicate()
        result = proc.returncode
        video_details = json.loads(out.decode())
    except Exception:
        try:  # try this again without -show error in case of ffmpeg limitation
            command = [
                nzb2media.FFPROBE,
                '-v',
                'quiet',
                print_format,
                'json',
                '-show_format',
                '-show_streams',
                videofile,
            ]
            print_cmd(command)
            if img:
                procin = zip_out(file, img, bitbucket)
                proc = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stdin=procin.stdout,
                )
                procin.stdout.close()
            else:
                proc = subprocess.Popen(command, stdout=subprocess.PIPE)
            out, err = proc.communicate()
            result = proc.returncode
            video_details = json.loads(out.decode())
        except Exception:
            log.error(f'Checking [{file}] has failed')
    return video_details, result


def check_vid_file(video_details, result):
    if result != 0:
        return False
    if video_details.get('error'):
        return False
    if not video_details.get('streams'):
        return False
    video_streams = [
        item
        for item in video_details['streams']
        if item['codec_type'] == 'video'
    ]
    audio_streams = [
        item
        for item in video_details['streams']
        if item['codec_type'] == 'audio'
    ]
    if len(video_streams) > 0 and len(audio_streams) > 0:
        return True
    else:
        return False


def build_commands(file, new_dir, movie_name, bitbucket):
    if isinstance(file, str):
        input_file = file
        if 'concat:' in file:
            file = file.split('|')[0].replace('concat:', '')
        video_details, result = get_video_details(file)
        directory, name = os.path.split(file)
        name, ext = os.path.splitext(name)
        check = re.match('VTS_([0-9][0-9])_[0-9]+', name)
        if check and nzb2media.CONCAT:
            name = movie_name
        elif check:
            name = f'{movie_name}.cd{check.groups()[0]}'
        elif nzb2media.CONCAT and re.match('(.+)[cC][dD][0-9]', name):
            name = re.sub('([ ._=:-]+[cC][dD][0-9])', '', name)
        if (
            ext == nzb2media.VEXTENSION and new_dir == directory
        ):  # we need to change the name to prevent overwriting itself.
            nzb2media.VEXTENSION = (
                f'-transcoded{nzb2media.VEXTENSION}'  # adds '-transcoded.ext'
            )
        new_file = file
    else:
        img, data = next(file.items())
        name = data['name']
        new_file = []
        rem_vid = []
        for vid in data['files']:
            video_details, result = get_video_details(vid, img, bitbucket)
            if not check_vid_file(
                video_details, result,
            ):  # lets not transcode menu or other clips that don't have audio and video.
                rem_vid.append(vid)
        data['files'] = [f for f in data['files'] if f not in rem_vid]
        new_file = {img: {'name': data['name'], 'files': data['files']}}
        video_details, result = get_video_details(
            data['files'][0], img, bitbucket,
        )
        input_file = '-'
        file = '-'

    newfile_path = os.path.normpath(
        os.path.join(new_dir, name) + nzb2media.VEXTENSION,
    )

    map_cmd = []
    video_cmd = []
    audio_cmd = []
    audio_cmd2 = []
    sub_cmd = []
    meta_cmd = []
    other_cmd = []

    if not video_details or not video_details.get(
        'streams',
    ):  # we couldn't read streams with ffprobe. Set defaults to try transcoding.
        video_streams = []
        audio_streams = []
        sub_streams = []

        map_cmd.extend(['-map', '0'])
        if nzb2media.VCODEC:
            video_cmd.extend(['-c:v', nzb2media.VCODEC])
            if nzb2media.VCODEC == 'libx264' and nzb2media.VPRESET:
                video_cmd.extend(['-pre', nzb2media.VPRESET])
        else:
            video_cmd.extend(['-c:v', 'copy'])
        if nzb2media.VFRAMERATE:
            video_cmd.extend(['-r', str(nzb2media.VFRAMERATE)])
        if nzb2media.VBITRATE:
            video_cmd.extend(['-b:v', str(nzb2media.VBITRATE)])
        if nzb2media.VRESOLUTION:
            video_cmd.extend(['-vf', f'scale={nzb2media.VRESOLUTION}'])
        if nzb2media.VPRESET:
            video_cmd.extend(['-preset', nzb2media.VPRESET])
        if nzb2media.VCRF:
            video_cmd.extend(['-crf', str(nzb2media.VCRF)])
        if nzb2media.VLEVEL:
            video_cmd.extend(['-level', str(nzb2media.VLEVEL)])

        if nzb2media.ACODEC:
            audio_cmd.extend(['-c:a', nzb2media.ACODEC])
            if nzb2media.ACODEC in [
                'aac',
                'dts',
            ]:  # Allow users to use the experimental AAC codec that's built into recent versions of ffmpeg
                audio_cmd.extend(['-strict', '-2'])
        else:
            audio_cmd.extend(['-c:a', 'copy'])
        if nzb2media.ACHANNELS:
            audio_cmd.extend(['-ac', str(nzb2media.ACHANNELS)])
        if nzb2media.ABITRATE:
            audio_cmd.extend(['-b:a', str(nzb2media.ABITRATE)])
        if nzb2media.OUTPUTQUALITYPERCENT:
            audio_cmd.extend(['-q:a', str(nzb2media.OUTPUTQUALITYPERCENT)])

        if nzb2media.SCODEC and nzb2media.ALLOWSUBS:
            sub_cmd.extend(['-c:s', nzb2media.SCODEC])
        elif (
            nzb2media.ALLOWSUBS
        ):  # Not every subtitle codec can be used for every video container format!
            sub_cmd.extend(['-c:s', 'copy'])
        else:  # http://en.wikibooks.org/wiki/FFMPEG_An_Intermediate_Guide/subtitle_options
            sub_cmd.extend(['-sn'])  # Don't copy the subtitles over

        if nzb2media.OUTPUTFASTSTART:
            other_cmd.extend(['-movflags', '+faststart'])

    else:
        video_streams = [
            item
            for item in video_details['streams']
            if item['codec_type'] == 'video'
        ]
        audio_streams = [
            item
            for item in video_details['streams']
            if item['codec_type'] == 'audio'
        ]
        sub_streams = [
            item
            for item in video_details['streams']
            if item['codec_type'] == 'subtitle'
        ]
        if nzb2media.VEXTENSION not in ['.mkv', '.mpegts']:
            sub_streams = [
                item
                for item in video_details['streams']
                if item['codec_type'] == 'subtitle'
                and item['codec_name'] != 'hdmv_pgs_subtitle'
                and item['codec_name'] != 'pgssub'
            ]

    for video in video_streams:
        codec = video['codec_name']
        fr = video.get('avg_frame_rate', 0)
        width = video.get('width', 0)
        height = video.get('height', 0)
        scale = nzb2media.VRESOLUTION
        if codec in nzb2media.VCODEC_ALLOW or not nzb2media.VCODEC:
            video_cmd.extend(['-c:v', 'copy'])
        else:
            video_cmd.extend(['-c:v', nzb2media.VCODEC])
        if nzb2media.VFRAMERATE and not (
                nzb2media.VFRAMERATE * 0.999 <= fr <= nzb2media.VFRAMERATE * 1.001
        ):
            video_cmd.extend(['-r', str(nzb2media.VFRAMERATE)])
        if scale:
            w_scale = width / float(scale.split(':')[0])
            h_scale = height / float(scale.split(':')[1])
            if w_scale > h_scale:  # widescreen, Scale by width only.
                scale = '{width}:{height}'.format(
                    width=scale.split(':')[0],
                    height=int((height / w_scale) / 2) * 2,
                )
                if w_scale > 1:
                    video_cmd.extend(['-vf', f'scale={scale}'])
            else:  # lower or matching ratio, scale by height only.
                scale = '{width}:{height}'.format(
                    width=int((width / h_scale) / 2) * 2,
                    height=scale.split(':')[1],
                )
                if h_scale > 1:
                    video_cmd.extend(['-vf', f'scale={scale}'])
        if nzb2media.VBITRATE:
            video_cmd.extend(['-b:v', str(nzb2media.VBITRATE)])
        if nzb2media.VPRESET:
            video_cmd.extend(['-preset', nzb2media.VPRESET])
        if nzb2media.VCRF:
            video_cmd.extend(['-crf', str(nzb2media.VCRF)])
        if nzb2media.VLEVEL:
            video_cmd.extend(['-level', str(nzb2media.VLEVEL)])
        no_copy = ['-vf', '-r', '-crf', '-level', '-preset', '-b:v']
        if video_cmd[1] == 'copy' and any(i in video_cmd for i in no_copy):
            video_cmd[1] = nzb2media.VCODEC
        if (
            nzb2media.VCODEC == 'copy'
        ):  # force copy. therefore ignore all other video transcoding.
            video_cmd = ['-c:v', 'copy']
        map_cmd.extend(['-map', '0:{index}'.format(index=video['index'])])
        break  # Only one video needed

    used_audio = 0
    a_mapped = []
    commentary = []
    if audio_streams:
        for i, val in reversed(list(enumerate(audio_streams))):
            try:
                if 'Commentary' in val.get('tags').get(
                    'title',
                ):  # Split out commentry tracks.
                    commentary.append(val)
                    del audio_streams[i]
            except Exception:
                continue
        try:
            audio1 = [
                item
                for item in audio_streams
                if item['tags']['language'] == nzb2media.ALANGUAGE
            ]
        except Exception:  # no language tags. Assume only 1 language.
            audio1 = audio_streams
        try:
            audio2 = [
                item
                for item in audio1
                if item['codec_name'] in nzb2media.ACODEC_ALLOW
            ]
        except Exception:
            audio2 = []
        try:
            audio3 = [
                item
                for item in audio_streams
                if item['tags']['language'] != nzb2media.ALANGUAGE
            ]
        except Exception:
            audio3 = []
        try:
            audio4 = [
                item
                for item in audio3
                if item['codec_name'] in nzb2media.ACODEC_ALLOW
            ]
        except Exception:
            audio4 = []

        if audio2:  # right (or only) language and codec...
            map_cmd.extend(
                ['-map', '0:{index}'.format(index=audio2[0]['index'])],
            )
            a_mapped.extend([audio2[0]['index']])
            bitrate = int(float(audio2[0].get('bit_rate', 0))) / 1000
            channels = int(float(audio2[0].get('channels', 0)))
            audio_cmd.extend([f'-c:a:{used_audio}', 'copy'])
        elif audio1:  # right (or only) language, wrong codec.
            map_cmd.extend(
                ['-map', '0:{index}'.format(index=audio1[0]['index'])],
            )
            a_mapped.extend([audio1[0]['index']])
            bitrate = int(float(audio1[0].get('bit_rate', 0))) / 1000
            channels = int(float(audio1[0].get('channels', 0)))
            audio_cmd.extend(
                [f'-c:a:{used_audio}', nzb2media.ACODEC if nzb2media.ACODEC else 'copy'],
            )
        elif audio4:  # wrong language, right codec.
            map_cmd.extend(
                ['-map', '0:{index}'.format(index=audio4[0]['index'])],
            )
            a_mapped.extend([audio4[0]['index']])
            bitrate = int(float(audio4[0].get('bit_rate', 0))) / 1000
            channels = int(float(audio4[0].get('channels', 0)))
            audio_cmd.extend([f'-c:a:{used_audio}', 'copy'])
        elif (
            audio3
        ):  # wrong language, wrong codec. just pick the default audio track
            map_cmd.extend(
                ['-map', '0:{index}'.format(index=audio3[0]['index'])],
            )
            a_mapped.extend([audio3[0]['index']])
            bitrate = int(float(audio3[0].get('bit_rate', 0))) / 1000
            channels = int(float(audio3[0].get('channels', 0)))
            audio_cmd.extend(
                [f'-c:a:{used_audio}', nzb2media.ACODEC if nzb2media.ACODEC else 'copy'],
            )

        if nzb2media.ACHANNELS and channels and channels > nzb2media.ACHANNELS:
            audio_cmd.extend([f'-ac:a:{used_audio}', str(nzb2media.ACHANNELS)])
            if audio_cmd[1] == 'copy':
                audio_cmd[1] = nzb2media.ACODEC
        if nzb2media.ABITRATE and not (
                nzb2media.ABITRATE * 0.9 < bitrate < nzb2media.ABITRATE * 1.1
        ):
            audio_cmd.extend([f'-b:a:{used_audio}', str(nzb2media.ABITRATE)])
            if audio_cmd[1] == 'copy':
                audio_cmd[1] = nzb2media.ACODEC
        if nzb2media.OUTPUTQUALITYPERCENT:
            audio_cmd.extend(
                [f'-q:a:{used_audio}', str(nzb2media.OUTPUTQUALITYPERCENT)],
            )
            if audio_cmd[1] == 'copy':
                audio_cmd[1] = nzb2media.ACODEC
        if audio_cmd[1] in ['aac', 'dts']:
            audio_cmd[2:2] = ['-strict', '-2']

        if nzb2media.ACODEC2_ALLOW:
            used_audio += 1
            try:
                audio5 = [
                    item
                    for item in audio1
                    if item['codec_name'] in nzb2media.ACODEC2_ALLOW
                ]
            except Exception:
                audio5 = []
            try:
                audio6 = [
                    item
                    for item in audio3
                    if item['codec_name'] in nzb2media.ACODEC2_ALLOW
                ]
            except Exception:
                audio6 = []
            if audio5:  # right language and codec.
                map_cmd.extend(
                    ['-map', '0:{index}'.format(index=audio5[0]['index'])],
                )
                a_mapped.extend([audio5[0]['index']])
                bitrate = int(float(audio5[0].get('bit_rate', 0))) / 1000
                channels = int(float(audio5[0].get('channels', 0)))
                audio_cmd2.extend([f'-c:a:{used_audio}', 'copy'])
            elif audio1:  # right language wrong codec.
                map_cmd.extend(
                    ['-map', '0:{index}'.format(index=audio1[0]['index'])],
                )
                a_mapped.extend([audio1[0]['index']])
                bitrate = int(float(audio1[0].get('bit_rate', 0))) / 1000
                channels = int(float(audio1[0].get('channels', 0)))
                if nzb2media.ACODEC2:
                    audio_cmd2.extend([f'-c:a:{used_audio}', nzb2media.ACODEC2])
                else:
                    audio_cmd2.extend([f'-c:a:{used_audio}', 'copy'])
            elif audio6:  # wrong language, right codec
                map_cmd.extend(
                    ['-map', '0:{index}'.format(index=audio6[0]['index'])],
                )
                a_mapped.extend([audio6[0]['index']])
                bitrate = int(float(audio6[0].get('bit_rate', 0))) / 1000
                channels = int(float(audio6[0].get('channels', 0)))
                audio_cmd2.extend([f'-c:a:{used_audio}', 'copy'])
            elif (
                audio3
            ):  # wrong language, wrong codec just pick the default audio track
                map_cmd.extend(
                    ['-map', '0:{index}'.format(index=audio3[0]['index'])],
                )
                a_mapped.extend([audio3[0]['index']])
                bitrate = int(float(audio3[0].get('bit_rate', 0))) / 1000
                channels = int(float(audio3[0].get('channels', 0)))
                if nzb2media.ACODEC2:
                    audio_cmd2.extend([f'-c:a:{used_audio}', nzb2media.ACODEC2])
                else:
                    audio_cmd2.extend([f'-c:a:{used_audio}', 'copy'])

            if nzb2media.ACHANNELS2 and channels and channels > nzb2media.ACHANNELS2:
                audio_cmd2.extend(
                    [f'-ac:a:{used_audio}', str(nzb2media.ACHANNELS2)],
                )
                if audio_cmd2[1] == 'copy':
                    audio_cmd2[1] = nzb2media.ACODEC2
            if nzb2media.ABITRATE2 and not (
                    nzb2media.ABITRATE2 * 0.9 < bitrate < nzb2media.ABITRATE2 * 1.1
            ):
                audio_cmd2.extend([f'-b:a:{used_audio}', str(nzb2media.ABITRATE2)])
                if audio_cmd2[1] == 'copy':
                    audio_cmd2[1] = nzb2media.ACODEC2
            if nzb2media.OUTPUTQUALITYPERCENT:
                audio_cmd2.extend(
                    [f'-q:a:{used_audio}', str(nzb2media.OUTPUTQUALITYPERCENT)],
                )
                if audio_cmd2[1] == 'copy':
                    audio_cmd2[1] = nzb2media.ACODEC2
            if audio_cmd2[1] in ['aac', 'dts']:
                audio_cmd2[2:2] = ['-strict', '-2']

            if (
                a_mapped[1] == a_mapped[0] and audio_cmd2[1:] == audio_cmd[1:]
            ):  # check for duplicate output track.
                del map_cmd[-2:]
            else:
                audio_cmd.extend(audio_cmd2)

        if nzb2media.AINCLUDE and nzb2media.ACODEC3:
            audio_streams.extend(commentary)  # add commentry tracks back here.
            for audio in audio_streams:
                if audio['index'] in a_mapped:
                    continue
                used_audio += 1
                map_cmd.extend(
                    ['-map', '0:{index}'.format(index=audio['index'])],
                )
                audio_cmd3 = []
                bitrate = int(float(audio.get('bit_rate', 0))) / 1000
                channels = int(float(audio.get('channels', 0)))
                if audio['codec_name'] in nzb2media.ACODEC3_ALLOW:
                    audio_cmd3.extend([f'-c:a:{used_audio}', 'copy'])
                else:
                    if nzb2media.ACODEC3:
                        audio_cmd3.extend([f'-c:a:{used_audio}', nzb2media.ACODEC3])
                    else:
                        audio_cmd3.extend([f'-c:a:{used_audio}', 'copy'])

                if nzb2media.ACHANNELS3 and channels and channels > nzb2media.ACHANNELS3:
                    audio_cmd3.extend(
                        [f'-ac:a:{used_audio}', str(nzb2media.ACHANNELS3)],
                    )
                    if audio_cmd3[1] == 'copy':
                        audio_cmd3[1] = nzb2media.ACODEC3
                if nzb2media.ABITRATE3 and not (
                        nzb2media.ABITRATE3 * 0.9 < bitrate < nzb2media.ABITRATE3 * 1.1
                ):
                    audio_cmd3.extend(
                        [f'-b:a:{used_audio}', str(nzb2media.ABITRATE3)],
                    )
                    if audio_cmd3[1] == 'copy':
                        audio_cmd3[1] = nzb2media.ACODEC3
                if nzb2media.OUTPUTQUALITYPERCENT > 0:
                    audio_cmd3.extend(
                        [f'-q:a:{used_audio}', str(nzb2media.OUTPUTQUALITYPERCENT)],
                    )
                    if audio_cmd3[1] == 'copy':
                        audio_cmd3[1] = nzb2media.ACODEC3
                if audio_cmd3[1] in ['aac', 'dts']:
                    audio_cmd3[2:2] = ['-strict', '-2']
                audio_cmd.extend(audio_cmd3)

    s_mapped = []
    burnt = 0
    n = 0
    for lan in nzb2media.SLANGUAGES:
        try:
            subs1 = [
                item for item in sub_streams if item['tags']['language'] == lan
            ]
        except Exception:
            subs1 = []
        if nzb2media.BURN and not subs1 and not burnt and os.path.isfile(file):
            for subfile in get_subs(file):
                if lan in os.path.split(subfile)[1]:
                    video_cmd.extend(['-vf', f'subtitles={subfile}'])
                    burnt = 1
        for sub in subs1:
            if nzb2media.BURN and not burnt and os.path.isfile(input_file):
                subloc = 0
                for index in range(len(sub_streams)):
                    if sub_streams[index]['index'] == sub['index']:
                        subloc = index
                        break
                video_cmd.extend(
                    ['-vf', f'subtitles={input_file}:si={subloc}'],
                )
                burnt = 1
            if not nzb2media.ALLOWSUBS:
                break
            if (
                sub['codec_name'] in ['dvd_subtitle', 'VobSub']
                and nzb2media.SCODEC == 'mov_text'
            ):  # We can't convert these.
                continue
            map_cmd.extend(['-map', '0:{index}'.format(index=sub['index'])])
            s_mapped.extend([sub['index']])

    if nzb2media.SINCLUDE:
        for sub in sub_streams:
            if not nzb2media.ALLOWSUBS:
                break
            if sub['index'] in s_mapped:
                continue
            if (
                sub['codec_name'] in ['dvd_subtitle', 'VobSub']
                and nzb2media.SCODEC == 'mov_text'
            ):  # We can't convert these.
                continue
            map_cmd.extend(['-map', '0:{index}'.format(index=sub['index'])])
            s_mapped.extend([sub['index']])

    if nzb2media.OUTPUTFASTSTART:
        other_cmd.extend(['-movflags', '+faststart'])
    if nzb2media.OTHEROPTS:
        other_cmd.extend(nzb2media.OTHEROPTS)

    command = [nzb2media.FFMPEG, '-loglevel', 'warning']

    if nzb2media.HWACCEL:
        command.extend(['-hwaccel', 'auto'])
    if nzb2media.GENERALOPTS:
        command.extend(nzb2media.GENERALOPTS)

    command.extend(['-i', input_file])

    if nzb2media.SEMBED and os.path.isfile(file):
        for subfile in get_subs(file):
            sub_details, result = get_video_details(subfile)
            if not sub_details or not sub_details.get('streams'):
                continue
            if nzb2media.SCODEC == 'mov_text':
                subcode = [
                    stream['codec_name'] for stream in sub_details['streams']
                ]
                if set(subcode).intersection(
                    ['dvd_subtitle', 'VobSub'],
                ):  # We can't convert these.
                    continue
            command.extend(['-i', subfile])
            lan = os.path.splitext(os.path.splitext(subfile)[0])[1][1:].split(
                '-',
            )[0]
            metlan = None
            try:
                if len(lan) == 3:
                    metlan = Language(lan)
                if len(lan) == 2:
                    metlan = Language.fromalpha2(lan)
            except Exception:
                pass
            if metlan:
                meta_cmd.extend(
                    [
                        f'-metadata:s:s:{len(s_mapped) + n}',
                        f'language={metlan.alpha3}',
                    ],
                )
            n += 1
            map_cmd.extend(['-map', f'{n}:0'])

    if not nzb2media.ALLOWSUBS or (not s_mapped and not n):
        sub_cmd.extend(['-sn'])
    else:
        if nzb2media.SCODEC:
            sub_cmd.extend(['-c:s', nzb2media.SCODEC])
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
        command = nzb2media.NICENESS + command
    return command, new_file


def get_subs(file):
    filepaths = []
    sub_ext = ['.srt', '.sub', '.idx']
    name = os.path.splitext(os.path.split(file)[1])[0]
    path = os.path.split(file)[0]
    for directory, _, filenames in os.walk(path):
        for filename in filenames:
            filepaths.extend([os.path.join(directory, filename)])
    subfiles = [
        item
        for item in filepaths
        if os.path.splitext(item)[1] in sub_ext and name in item
    ]
    return subfiles


def extract_subs(file, newfile_path, bitbucket):
    video_details, result = get_video_details(file)
    if not video_details:
        return

    if nzb2media.SUBSDIR:
        subdir = nzb2media.SUBSDIR
    else:
        subdir = os.path.split(newfile_path)[0]
    name = os.path.splitext(os.path.split(newfile_path)[1])[0]

    try:
        sub_streams = [
            item
            for item in video_details['streams']
            if item['codec_type'] == 'subtitle'
            and item['tags']['language'] in nzb2media.SLANGUAGES
            and item['codec_name'] != 'hdmv_pgs_subtitle'
            and item['codec_name'] != 'pgssub'
        ]
    except Exception:
        sub_streams = [
            item
            for item in video_details['streams']
            if item['codec_type'] == 'subtitle'
            and item['codec_name'] != 'hdmv_pgs_subtitle'
            and item['codec_name'] != 'pgssub'
        ]
    num = len(sub_streams)
    for n in range(num):
        sub = sub_streams[n]
        idx = sub['index']
        lan = sub.get('tags', {}).get('language', 'unk')

        if num == 1:
            output_file = os.path.join(subdir, f'{name}.srt')
            if os.path.isfile(output_file):
                output_file = os.path.join(subdir, f'{name}.{n}.srt')
        else:
            output_file = os.path.join(subdir, f'{name}.{lan}.srt')
            if os.path.isfile(output_file):
                output_file = os.path.join(subdir, f'{name}.{lan}.{n}.srt')

        command = [
            nzb2media.FFMPEG,
            '-loglevel',
            'warning',
            '-i',
            file,
            '-vn',
            '-an',
            f'-codec:{idx}',
            'srt',
            output_file,
        ]
        if platform.system() != 'Windows':
            command = nzb2media.NICENESS + command

        log.info(f'Extracting {lan} subtitle from: {file}')
        print_cmd(command)
        result = 1  # set result to failed in case call fails.
        try:
            proc = subprocess.Popen(
                command, stdout=bitbucket, stderr=bitbucket,
            )
            out, err = proc.communicate()
            result = proc.returncode
        except Exception:
            log.error('Extracting subtitle has failed')

        if result == 0:
            try:
                shutil.copymode(file, output_file)
            except Exception:
                pass
            log.info(f'Extracting {lan} subtitle from {file} has succeeded')
        else:
            log.error('Extracting subtitles has failed')


def process_list(it, new_dir, bitbucket):
    rem_list = []
    new_list = []
    combine = []
    vts_path = None
    mts_path = None
    success = True
    for item in it:
        ext = os.path.splitext(item)[1].lower()
        if (
            ext in ['.iso', '.bin', '.img']
            and ext not in nzb2media.IGNOREEXTENSIONS
        ):
            log.debug(f'Attempting to rip disk image: {item}')
            new_list.extend(rip_iso(item, new_dir, bitbucket))
            rem_list.append(item)
        elif (
                re.match('.+VTS_[0-9][0-9]_[0-9].[Vv][Oo][Bb]', item)
                and '.vob' not in nzb2media.IGNOREEXTENSIONS
        ):
            log.debug(f'Found VIDEO_TS image file: {item}')
            if not vts_path:
                try:
                    vts_path = re.match('(.+VIDEO_TS)', item).groups()[0]
                except Exception:
                    vts_path = os.path.split(item)[0]
            rem_list.append(item)
        elif (
                re.match('.+BDMV[/\\]SOURCE[/\\][0-9]+[0-9].[Mm][Tt][Ss]', item)
                and '.mts' not in nzb2media.IGNOREEXTENSIONS
        ):
            log.debug(f'Found MTS image file: {item}')
            if not mts_path:
                try:
                    mts_path = re.match('(.+BDMV[/\\]SOURCE)', item).groups()[
                        0
                    ]
                except Exception:
                    mts_path = os.path.split(item)[0]
            rem_list.append(item)
        elif re.match('.+VIDEO_TS.', item) or re.match(
            '.+VTS_[0-9][0-9]_[0-9].', item,
        ):
            rem_list.append(item)
        elif nzb2media.CONCAT and re.match('.+[cC][dD][0-9].', item):
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
        if (
            isinstance(file, str)
            and 'concat:' not in file
            and not os.path.isfile(file)
        ):
            success = False
            break
    if success and new_list:
        it.extend(new_list)
        for item in rem_list:
            it.remove(item)
        log.debug(f'Successfully extracted .vob file {new_list[0]} from disk image')
    elif new_list and not success:
        new_list = []
        rem_list = []
        log.error('Failed extracting .vob files from disk image. Stopping transcoding.')
    return it, rem_list, new_list, success


def mount_iso(
    item, new_dir, bitbucket,
):  # Currently only supports Linux Mount when permissions allow.
    if platform.system() == 'Windows':
        log.error(f'No mounting options available under Windows for image file {item}')
        return []
    mount_point = os.path.join(os.path.dirname(os.path.abspath(item)), 'temp')
    make_dir(mount_point)
    cmd = ['mount', '-o', 'loop', item, mount_point]
    print_cmd(cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=bitbucket)
    out, err = proc.communicate()
    nzb2media.MOUNTED = (
        mount_point  # Allows us to verify this has been done and then cleanup.
    )
    for root, dirs, files in os.walk(mount_point):
        for file in files:
            full_path = os.path.join(root, file)
            if (
                re.match('.+VTS_[0-9][0-9]_[0-9].[Vv][Oo][Bb]', full_path)
                and '.vob' not in nzb2media.IGNOREEXTENSIONS
            ):
                log.debug(f'Found VIDEO_TS image file: {full_path}')
                try:
                    vts_path = re.match('(.+VIDEO_TS)', full_path).groups()[0]
                except Exception:
                    vts_path = os.path.split(full_path)[0]
                return combine_vts(vts_path)
            elif (
                    re.match('.+BDMV[/\\]STREAM[/\\][0-9]+[0-9].[Mm]', full_path)
                    and '.mts' not in nzb2media.IGNOREEXTENSIONS
            ):
                log.debug(f'Found MTS image file: {full_path}')
                try:
                    mts_path = re.match(
                        '(.+BDMV[/\\]STREAM)', full_path,
                    ).groups()[0]
                except Exception:
                    mts_path = os.path.split(full_path)[0]
                return combine_mts(mts_path)
    log.error(f'No VIDEO_TS or BDMV/SOURCE folder found in image file {mount_point}')
    return ['failure']  # If we got here, nothing matched our criteria


def rip_iso(item, new_dir, bitbucket):
    new_files = []
    failure_dir = 'failure'
    # Mount the ISO in your OS and call combineVTS.
    if not nzb2media.SEVENZIP:
        log.debug(f'No 7zip installed. Attempting to mount image file {item}')
        try:
            new_files = mount_iso(
                item, new_dir, bitbucket,
            )  # Currently only works for Linux.
        except Exception:
            log.error(f'Failed to mount and extract from image file {item}')
            new_files = [failure_dir]
        return new_files
    cmd = [nzb2media.SEVENZIP, 'l', item]
    try:
        log.debug(f'Attempting to extract .vob or .mts from image file {item}')
        print_cmd(cmd)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=bitbucket)
        out, err = proc.communicate()
        file_match_gen = (
            re.match(
                r'.+(VIDEO_TS[/\\]VTS_[0-9][0-9]_[0-9].[Vv][Oo][Bb])', line,
            )
            for line in out.decode().splitlines()
        )
        file_list = [
            file_match.groups()[0]
            for file_match in file_match_gen
            if file_match
        ]
        combined = []
        if file_list:  # handle DVD
            for n in range(99):
                concat = []
                m = 1
                while True:
                    vts_name = f'VIDEO_TS{os.sep}VTS_{n + 1:02d}_{m:d}.VOB'
                    if vts_name in file_list:
                        concat.append(vts_name)
                        m += 1
                    else:
                        break
                if not concat:
                    break
                if nzb2media.CONCAT:
                    combined.extend(concat)
                    continue
                name = '{name}.cd{x}'.format(
                    name=os.path.splitext(os.path.split(item)[1])[0],
                    x=n + 1,
                )
                new_files.append({item: {'name': name, 'files': concat}})
        else:  # check BlueRay for BDMV/STREAM/XXXX.MTS
            mts_list_gen = (
                re.match(r'.+(BDMV[/\\]STREAM[/\\][0-9]+[0-9].[Mm]).', line)
                for line in out.decode().splitlines()
            )
            mts_list = [
                file_match.groups()[0]
                for file_match in mts_list_gen
                if file_match
            ]
            if sys.version_info[0] == 2:  # Python2 sorting
                mts_list.sort(
                    key=lambda f: int(filter(str.isdigit, f)),
                )  # Sort all .mts files in numerical order
            else:  # Python3 sorting
                mts_list.sort(
                    key=lambda f: int(''.join(filter(str.isdigit, f))),
                )
            n = 0
            for mts_name in mts_list:
                concat = []
                n += 1
                concat.append(mts_name)
                if nzb2media.CONCAT:
                    combined.extend(concat)
                    continue
                name = '{name}.cd{x}'.format(
                    name=os.path.splitext(os.path.split(item)[1])[0],
                    x=n,
                )
                new_files.append({item: {'name': name, 'files': concat}})
        if nzb2media.CONCAT and combined:
            name = os.path.splitext(os.path.split(item)[1])[0]
            new_files.append({item: {'name': name, 'files': combined}})
        if not new_files:
            log.error(f'No VIDEO_TS or BDMV/SOURCE folder found in image file. Attempting to mount and scan {item}')
            new_files = mount_iso(item, new_dir, bitbucket)
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
    for n in range(99):
        concat = []
        m = 1
        while True:
            vts_name = f'VTS_{n + 1:02d}_{m:d}.VOB'
            if os.path.isfile(os.path.join(vts_path, vts_name)):
                concat.append(os.path.join(vts_path, vts_name))
                m += 1
            else:
                break
        if not concat:
            break
        if nzb2media.CONCAT:
            combined.extend(concat)
            continue
        name = '{name}.cd{x}'.format(
            name=name,
            x=n + 1,
        )
        new_files.append({vts_path: {'name': name, 'files': concat}})
    if nzb2media.CONCAT:
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
    n = 0
    mts_list = [
        f
        for f in os.listdir(mts_path)
        if os.path.isfile(os.path.join(mts_path, f))
    ]
    if sys.version_info[0] == 2:  # Python2 sorting
        mts_list.sort(key=lambda f: int(filter(str.isdigit, f)))
    else:  # Python3 sorting
        mts_list.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
    for mts_name in mts_list:  # need to sort all files [1 - 998].mts in order
        concat = []
        concat.append(os.path.join(mts_path, mts_name))
        if nzb2media.CONCAT:
            combined.extend(concat)
            continue
        name = '{name}.cd{x}'.format(
            name=name,
            x=n + 1,
        )
        new_files.append({mts_path: {'name': name, 'files': concat}})
        n += 1
    if nzb2media.CONCAT:
        new_files.append({mts_path: {'name': name, 'files': combined}})
    return new_files


def combine_cd(combine):
    new_files = []
    for item in {
        re.match('(.+)[cC][dD][0-9].', item).groups()[0] for item in combine
    }:
        concat = ''
        for n in range(99):
            files = [
                file
                for file in combine
                if n + 1
                == int(re.match('.+[cC][dD]([0-9]+).', file).groups()[0])
                and item in file
            ]
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
    if not nzb2media.FFMPEG:
        return 1, dir_name
    log.info('Checking for files to be transcoded')
    final_result = 0  # initialize as successful
    if nzb2media.OUTPUTVIDEOPATH:
        new_dir = nzb2media.OUTPUTVIDEOPATH
        make_dir(new_dir)
        name = os.path.splitext(os.path.split(dir_name)[1])[0]
        new_dir = os.path.join(new_dir, name)
        make_dir(new_dir)
    else:
        new_dir = dir_name
    if platform.system() == 'Windows':
        bitbucket = open('NUL')
    else:
        bitbucket = open('/dev/null')
    movie_name = os.path.splitext(os.path.split(dir_name)[1])[0]
    file_list = nzb2media.list_media_files(
        dir_name, media=True, audio=False, meta=False, archives=False,
    )
    file_list, rem_list, new_list, success = process_list(
        file_list, new_dir, bitbucket,
    )
    if not success:
        bitbucket.close()
        return 1, dir_name

    for file in file_list:
        if (
            isinstance(file, str)
            and os.path.splitext(file)[1] in nzb2media.IGNOREEXTENSIONS
        ):
            continue
        command, file = build_commands(file, new_dir, movie_name, bitbucket)
        newfile_path = command[-1]

        # transcoding files may remove the original file, so make sure to extract subtitles first
        if nzb2media.SEXTRACT and isinstance(file, str):
            extract_subs(file, newfile_path, bitbucket)

        try:  # Try to remove the file that we're transcoding to just in case. (ffmpeg will return an error if it already exists for some reason)
            os.remove(newfile_path)
        except OSError as error:
            if (
                error.errno != errno.ENOENT
            ):  # Ignore the error if it's just telling us that the file doesn't exist
                log.debug(f'Error when removing transcoding target: {error}')
        except Exception as error:
            log.debug(f'Error when removing transcoding target: {error}')

        log.info(f'Transcoding video: {newfile_path}')
        print_cmd(command)
        result = 1  # set result to failed in case call fails.
        try:
            if isinstance(file, str):
                proc = subprocess.Popen(
                    command, stdout=bitbucket, stderr=subprocess.PIPE,
                )
            else:
                img, data = next(file.items())
                proc = subprocess.Popen(
                    command,
                    stdout=bitbucket,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                )
                for vob in data['files']:
                    procin = zip_out(vob, img, bitbucket)
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

        if nzb2media.SUBSDIR and result == 0 and isinstance(file, str):
            for sub in get_subs(file):
                name = os.path.splitext(os.path.split(file)[1])[0]
                subname = os.path.split(sub)[1]
                newname = os.path.splitext(os.path.split(newfile_path)[1])[0]
                newpath = os.path.join(
                    nzb2media.SUBSDIR, subname.replace(name, newname),
                )
                if not os.path.isfile(newpath):
                    os.rename(sub, newpath)

        if result == 0:
            try:
                shutil.copymode(file, newfile_path)
            except Exception:
                pass
            log.info(f'Transcoding of video to {newfile_path} succeeded')
            if os.path.isfile(newfile_path) and (
                file in new_list or not nzb2media.DUPLICATE
            ):
                try:
                    os.unlink(file)
                except Exception:
                    pass
        else:
            log.error(f'Transcoding of video to {newfile_path} failed with result {result}')
        # this will be 0 (successful) it all are successful, else will return a positive integer for failure.
        final_result = final_result + result
    if nzb2media.MOUNTED:  # In case we mounted an .iso file, unmount here.
        time.sleep(5)  # play it safe and avoid failing to unmount.
        cmd = ['umount', '-l', nzb2media.MOUNTED]
        print_cmd(cmd)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=bitbucket)
        out, err = proc.communicate()
        time.sleep(5)
        os.rmdir(nzb2media.MOUNTED)
        nzb2media.MOUNTED = None
    if final_result == 0 and not nzb2media.DUPLICATE:
        for file in rem_list:
            try:
                os.unlink(file)
            except Exception:
                pass
    if not os.listdir(
        new_dir,
    ):  # this is an empty directory and we didn't transcode into it.
        os.rmdir(new_dir)
        new_dir = dir_name
    if (
        not nzb2media.PROCESSOUTPUT and nzb2media.DUPLICATE
    ):  # We postprocess the original files to CP/SB
        new_dir = dir_name
    bitbucket.close()
    return final_result, new_dir
