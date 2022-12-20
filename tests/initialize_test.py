#! /usr/bin/env python
from __future__ import annotations

import nzb2media


def test_initial():
    nzb2media.initialize()


def test_core_parameters():
    assert nzb2media.CHECK_MEDIA == 1
