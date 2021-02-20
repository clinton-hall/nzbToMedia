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
