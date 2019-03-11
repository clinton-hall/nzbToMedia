#! /usr/bin/env python
from __future__ import print_function
from __future__ import absolute_import

import eol
eol.check()

import cleanup
cleanup.clean(cleanup.FOLDER_STRUCTURE)

import datetime
import os
import sys

import core
from core import logger, main_db
from core.auto_process import comics, games, movies, music, tv
from core.auto_process.common import ProcessResult
from core.plugins.downloaders.nzb.utils import get_nzoid
from core.plugins.plex import plex_update
from core.user_scripts import external_script
from core.utils import (
    char_replace, clean_dir, convert_to_ascii,
    extract_files, get_dirs, get_download_info,
    update_download_info_status,
)

# Initialize the config
core.initialize()

# label = core.TORRENT_CLASS.core.get_torrent_status('f33a9c4b15cbd9170722d700069af86746817ade', ['label']).get()['label']
# print(label)

#if transcoder.is_video_good(core.TEST_FILE, 0):
#    print('FFPROBE Works')
#else:
#    print('FFPROBE FAILED')

test = core.CFG['SickBeard', 'NzbDrone']['tv'].isenabled()
print(test)
section = core.CFG.findsection('tv').isenabled()
print(section)
print(len(section))
#fork, fork_params = auto_fork('SickBeard', 'tv')

#if server_responding('http://127.0.0.1:5050'):
#    print('CouchPotato Running')
#if server_responding('http://127.0.0.1:7073'):
#    print('SickBeard Running')
#if server_responding('http://127.0.0.1:8181'):
#    print('HeadPhones Running')
#if server_responding('http://127.0.0.1:8085'):
#    print('Gamez Running')
#if server_responding('http://127.0.0.1:8090'):
#    print('Mylar Running')

#lan = 'pt'
#lan = Language.fromalpha2(lan)
#print(lan.alpha3)
#vidName = '/volume1/Public/Movies/A Few Good Men/A Few Good Men(1992).mkv'
#inputName = 'in.the.name.of.ben.hur.2016.bdrip.x264-rusted.nzb'
#guess = guessit.guessit(inputName)
#if guess:
    # Movie Title
#    title = None
#    if 'title' in guess:
#        title = guess['title']
    # Movie Year
#    year = None
#    if 'year' in guess:
#        year = guess['year']
#    url = 'http://www.omdbapi.com'
#    r = requests.get(url, params={'y': year, 't': title}, verify=False, timeout=(60, 300))
#    results = r.json()
#    print(results)

#subliminal.region.configure('dogpile.cache.dbm', arguments={'filename': 'cachefile.dbm'})
#languages = set()
#languages.add(lan)
#video = subliminal.scan_video(vidName)
#subtitles = subliminal.download_best_subtitles({video}, languages)
#subliminal.save_subtitles(video, subtitles[video])
del core.MYAPP
