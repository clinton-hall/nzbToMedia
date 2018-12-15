# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

from .client import Client
from .constants import DEFAULT_PORT, DEFAULT_TIMEOUT, LOGGER, PRIORITY, RATIO_LIMIT
from .error import HTTPHandlerError, TransmissionError
from .httphandler import DefaultHTTPHandler, HTTPHandler
from .session import Session
from .torrent import Torrent
from .utils import add_file_logger, add_stdout_logger

__author__ = 'Erik Svensson <erik.public@gmail.com>'
__version_major__ = 0
__version_minor__ = 11
__version__ = '{0}.{1}'.format(__version_major__, __version_minor__)
__copyright__ = 'Copyright (c) 2008-2013 Erik Svensson'
__license__ = 'MIT'
