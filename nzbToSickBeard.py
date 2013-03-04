#!/usr/bin/env python

# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.
#
# Edited by Clinton Hall to prevent processing of failed downloads.
# Also added suppot for NZBGet. With help from thorli


import sys
import logging

import autoProcessTV
from nzbToMediaEnv import *
from nzbToMediaUtil import *

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToSickBeard %s", VERSION)

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
    Logger.info("Script triggered from SABnzbd, starting autoProcessTV...")
    result = autoProcessTV.processEpisode(sys.argv[1], sys.argv[2], sys.argv[7])

# NZBGet
elif len(sys.argv) == 4:
# NZBGet argv:
# 1  The final directory of the job (full path)
# 2  The original name of the NZB file
# 3  The status of the download: 0 == successful
    Logger.info("Script triggered from NZBGet, starting autoProcessTV...")
    result = autoProcessTV.processEpisode(sys.argv[1], sys.argv[2], sys.argv[3])

else:
    Logger.debug("Invalid number of arguments received from client.")
    Logger.info("Running autoProcessTV as a manual run...")
    result = autoProcessTV.processEpisode('Manual Run', 'Manual Run', 0)
