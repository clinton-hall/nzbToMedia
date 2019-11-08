#! /usr/bin/env python
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import core
from core import transcoder


def test_transcoder_check():
    assert transcoder.is_video_good(core.TEST_FILE, 1) is True
