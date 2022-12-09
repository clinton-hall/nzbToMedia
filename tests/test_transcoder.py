#! /usr/bin/env python

import core
from core import transcoder


def test_transcoder_check():
    assert transcoder.is_video_good(core.TEST_FILE, 1) is True
