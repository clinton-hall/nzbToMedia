# -*- coding: utf-8 -*-
# Copyright (c) 2008-2013 Erik Svensson <erik.public@gmail.com>
# Licensed under the MIT license.

from nzbtomedia.transmissionrpc.constants import DEFAULT_PORT, DEFAULT_TIMEOUT, PRIORITY, RATIO_LIMIT, LOGGER
from nzbtomedia.transmissionrpc.error import TransmissionError, HTTPHandlerError
from nzbtomedia.transmissionrpc.httphandler import HTTPHandler, DefaultHTTPHandler
from nzbtomedia.transmissionrpc.torrent import Torrent
from nzbtomedia.transmissionrpc.session import Session
from nzbtomedia.transmissionrpc.client import Client
from nzbtomedia.transmissionrpc.utils import add_stdout_logger, add_file_logger

__author__    		= 'Erik Svensson <erik.public@gmail.com>'
__version_major__   = 0
__version_minor__   = 11
__version__   		= '{0}.{1}'.format(__version_major__, __version_minor__)
__copyright__ 		= 'Copyright (c) 2008-2013 Erik Svensson'
__license__   		= 'MIT'
