#! /usr/bin/env python
from __future__ import annotations

import nzb2media
from nzb2media import transcoder


def test_transcoder_check():
    assert transcoder.is_video_good(nzb2media.TEST_FILE, 1) is True
