#! /usr/bin/env python
from __future__ import print_function

import core
from core import transcoder


def test_transcoder_check():
    assert transcoder.is_video_good(core.TEST_FILE, 0) is True
