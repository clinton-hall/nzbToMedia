from __future__ import annotations

import logging
import os
import re

import subliminal
from babelfish import Language

import nzb2media

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def import_subs(filename):
    if not nzb2media.GETSUBS:
        return
    try:
        subliminal.region.configure(
            'dogpile.cache.dbm', arguments={'filename': 'cachefile.dbm'},
        )
    except Exception:
        pass

    languages = set()
    for item in nzb2media.SLANGUAGES:
        try:
            languages.add(Language(item))
        except Exception:
            pass
    if not languages:
        return

    log.info(f'Attempting to download subtitles for {filename}')
    try:
        video = subliminal.scan_video(filename)
        subtitles = subliminal.download_best_subtitles({video}, languages)
        subliminal.save_subtitles(video, subtitles[video])

        for subtitle in subtitles[video]:
            subtitle_path = subliminal.subtitle.get_subtitle_path(
                video.name, subtitle.language,
            )
            os.chmod(subtitle_path, 0o644)
    except Exception as error:
        log.error(f'Failed to download subtitles for {filename} due to: {error}')


def rename_subs(path):
    filepaths = []
    sub_ext = ['.srt', '.sub', '.idx']
    vidfiles = nzb2media.list_media_files(
        path, media=True, audio=False, meta=False, archives=False,
    )
    if (
        not vidfiles or len(vidfiles) > 1
    ):  # If there is more than 1 video file, or no video files, we can't rename subs.
        return
    name = os.path.splitext(os.path.split(vidfiles[0])[1])[0]
    for directory, _, filenames in os.walk(path):
        for filename in filenames:
            filepaths.extend([os.path.join(directory, filename)])
    subfiles = [
        item for item in filepaths if os.path.splitext(item)[1] in sub_ext
    ]
    subfiles.sort()  # This should sort subtitle names by language (alpha) and Number (where multiple)
    renamed = []
    for sub in subfiles:
        subname, ext = os.path.splitext(os.path.basename(sub))
        if (
            name in subname
        ):  # The sub file name already includes the video name.
            continue
        words = re.findall(
            '[a-zA-Z]+', str(subname),
        )  # find whole words in string
        # parse the words for language descriptors.
        lan = None
        for word in words:
            try:
                if len(word) == 2:
                    lan = Language.fromalpha2(word.lower())
                elif len(word) == 3:
                    lan = Language(word.lower())
                elif len(word) > 3:
                    lan = Language.fromname(word.lower())
                if lan:
                    break
            except:  # if we didn't find a language, try next word.
                continue
        # rename the sub file as name.lan.ext
        if not lan:
            # could call ffprobe to parse the sub information and get language if lan unknown here.
            new_sub_name = name
        else:
            new_sub_name = f'{name}.{str(lan)}'
        new_sub = os.path.join(
            directory, new_sub_name,
        )  # full path and name less ext
        if (
            f'{new_sub}{ext}' in renamed
        ):  # If duplicate names, add unique number before ext.
            for i in range(1, len(renamed) + 1):
                if f'{new_sub}.{i}{ext}' in renamed:
                    continue
                new_sub = f'{new_sub}.{i}'
                break
        new_sub = f'{new_sub}{ext}'  # add extension now
        if os.path.isfile(new_sub):  # Don't copy over existing - final check.
            log.debug(f'Unable to rename sub file {sub} as destination {new_sub} already exists')
            continue
        log.debug(f'Renaming sub file from {sub} to {new_sub}')
        renamed.append(new_sub)
        try:
            os.rename(sub, new_sub)
        except Exception as error:
            log.error(f'Unable to rename sub file due to: {error}')
    return
