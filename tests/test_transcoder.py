#! /usr/bin/env python
from __future__ import print_function
import datetime
import os
import sys
import json
import time
import requests

import core
from core import logger, transcoder

def test_transcoder_check():
    assert transcoder.is_video_good(core.TEST_FILE, 0) == True
