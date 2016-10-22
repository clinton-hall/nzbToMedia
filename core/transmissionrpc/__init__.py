# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

from core.transmissionrpc.constants import DEFAULT_PORT, DEFAULT_TIMEOUT, PRIORITY, RATIO_LIMIT, LOGGER
from core.transmissionrpc.error import TransmissionError, HTTPHandlerError
from core.transmissionrpc.httphandler import HTTPHandler, DefaultHTTPHandler
from core.transmissionrpc.torrent import Torrent
from core.transmissionrpc.session import Session
from core.transmissionrpc.client import Client
from core.transmissionrpc.utils import add_stdout_logger, add_file_logger

__author__ = 'Erik Svensson <erik.public@gmail.com>'
__version_major__ = 0
__version_minor__ = 11
__version__ = '{0}.{1}'.format(__version_major__, __version_minor__)
__copyright__ = 'Copyright (c) 2008-2013 Erik Svensson'
__license__ = 'MIT'
