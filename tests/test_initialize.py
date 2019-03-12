#! /usr/bin/env python
from __future__ import print_function
import datetime
import os
import sys

def test_eol()
    import eol
    eol.check()

def test_cleanup():
    import cleanup
    cleanup.clean(cleanup.FOLDER_STRUCTURE)

def test_import_core():
    import core
    from core import logger, main_db

def test_import_core_auto_process():
    from core.auto_process import comics, games, movies, music, tv
    from core.auto_process.common import ProcessResult

def test_import_core_plugins():
    from core.plugins.downloaders.nzb.utils import get_nzoid
    from core.plugins.plex import plex_update

def test_import_core_user_scripts():
    from core.user_scripts import external_script

def test_import_six():
    from six import text_type

def test_import_core_utils():
    from core.utils import (
        char_replace, clean_dir, convert_to_ascii,
        extract_files, get_dirs, get_download_info,
        update_download_info_status, replace_links,
    )

def test_initial():
    core.initialize()
    del core.MYAPP

def test_answer():
    assert core.CHECK_MEDIA == 1
