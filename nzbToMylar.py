#!/usr/bin/env python

import sys
import logging

import autoProcessComics
from nzbToMediaEnv import *
from nzbToMediaUtil import *

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToMylar %s", VERSION)

# SABnzbd
if len(sys.argv) == 8:
# SABnzbd argv:
# 1 The final directory of the job (full path)
# 2 The original name of the NZB file
# 3 Clean version of the job name (no path info and ".nzb" removed)
# 4 Indexer's report number (if supported)
# 5 User-defined category
# 6 Group that the NZB was posted in e.g. alt.binaries.x
# 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
  Logger.info("Script triggered from SABnzbd, starting autoProcessComics...")
	result = autoProcessComics.processEpisode(sys.argv[1], sys.argv[3])

# NZBGet
elif len(sys.argv) == 4:
# NZBGet argv:
# 1  The final directory of the job (full path)
# 2  The original name of the NZB file
# 3  The status of the download: 0 == successful
	Logger.info("Script triggered from NZBGet, starting autoProcessComics...")
	result = autoProcessComics.processEpisode(sys.argv[1], sys.argv[2])

else:
	Logger.warn("Invalid number of arguments received from client. Exiting")
	sys.exit(-1)
