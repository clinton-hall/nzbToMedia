from __future__ import annotations

import sys

import pytest

import nzb2media
from nzb2media import transcoder


@pytest.mark.xfail(
    sys.platform == 'win32' and sys.version_info < (3, 8),
    reason='subprocess.Popen does not support pathlib.Path commands in Python 3.7',
)
def test_transcoder_check():
    assert transcoder.is_video_good(nzb2media.TEST_FILE, 1) is True
