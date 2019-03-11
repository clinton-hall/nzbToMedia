#! /usr/bin/env python
from __future__ import print_function

import datetime
import os
import sys
sys.path.extend(["..","."])

import eol
eol.check()

import cleanup
cleanup.clean(cleanup.FOLDER_STRUCTURE)

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
del core.MYAPP

def test_answer():
    assert core.CHECK_MEDIA == 1
