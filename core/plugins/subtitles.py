from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from babelfish import Language
import subliminal

import core
from core import logger

import os
import re

for provider in subliminal.provider_manager.internal_extensions:
    if provider not in [str(x) for x in subliminal.provider_manager.list_entry_points()]:
        subliminal.provider_manager.register(str(provider))


def import_subs(filename):
    if not core.GETSUBS:
        return
    try:
        subliminal.region.configure('dogpile.cache.dbm', arguments={'filename': 'cachefile.dbm'})
    except Exception:
        pass

    languages = set()
    for item in core.SLANGUAGES:
        try:
            languages.add(Language(item))
        except Exception:
            pass
    if not languages:
        return

    logger.info('Attempting to download subtitles for {0}'.format(filename), 'SUBTITLES')
    try:
        video = subliminal.scan_video(filename)
        subtitles = subliminal.download_best_subtitles({video}, languages)
        subliminal.save_subtitles(video, subtitles[video])
        
        for subtitle in subtitles[video]:
            subtitle_path = subliminal.subtitle.get_subtitle_path(video.name, subtitle.language)
            os.chmod(subtitle_path, 0o644)
    except Exception as e:
        logger.error('Failed to download subtitles for {0} due to: {1}'.format(filename, e), 'SUBTITLES')

def rename_subs(path):
    filepaths = []
    sub_ext = ['.srt', '.sub', '.idx']
    vidfiles = core.list_media_files(path, media=True, audio=False, meta=False, archives=False)
    if not vidfiles or len(vidfiles) > 1: # If there is more than 1 video file, or no video files, we can't rename subs.
        return
    name = os.path.splitext(os.path.split(vidfiles[0])[1])[0]
    for directory, _, filenames in os.walk(path):
        for filename in filenames:
            filepaths.extend([os.path.join(directory, filename)])
    subfiles = [item for item in filepaths if os.path.splitext(item)[1] in sub_ext]
    subfiles.sort() #This should sort subtitle names by language (alpha) and Number (where multiple)
    renamed = []
    for sub in subfiles:
        subname, ext = os.path.splitext(os.path.basename(sub))
        if name in subname: # The sub file name already includes the video name.
            continue
        words = re.findall('[a-zA-Z]+',str(subname)) # find whole words in string
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
            except: #if we didn't find a language, try next word.
                continue
        # rename the sub file as name.lan.ext
        if not lan:
            # could call ffprobe to parse the sub information and get language if lan unknown here.
            new_sub_name = name
        else:
            new_sub_name = '{name}.{lan}'.format(name=name, lan=str(lan))
        new_sub = os.path.join(directory, new_sub_name) # full path and name less ext
        if '{new_sub}{ext}'.format(new_sub=new_sub, ext=ext) in renamed: # If duplicate names, add unique number before ext.
            for i in range(1,len(renamed)+1):
                if '{new_sub}.{i}{ext}'.format(new_sub=new_sub, i=i, ext=ext) in renamed:
                    continue
                new_sub = '{new_sub}.{i}'.format(new_sub=new_sub, i=i)
                break
        new_sub = '{new_sub}{ext}'.format(new_sub=new_sub, ext=ext) # add extension now
        if os.path.isfile(new_sub): # Don't copy over existing - final check.
            logger.debug('Unable to rename sub file {old} as destination {new} already exists'.format(old=sub, new=new_sub))
            continue
        logger.debug('Renaming sub file from {old} to {new}'.format
                 (old=sub, new=new_sub))
        renamed.append(new_sub)
        try:
            os.rename(sub, new_sub)
        except Exception as error:
            logger.error('Unable to rename sub file due to: {error}'.format(error=error))
    return
