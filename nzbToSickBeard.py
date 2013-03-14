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
sys.path.insert(0, 'autoProcess/') # add this folder to path as this allows out-of-sight files to be called.
import logging

import migratecfg
import autoProcessTV
from nzbToMediaEnv import *
from nzbToMediaUtil import *

#check to migrate old cfg before trying to load.
if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
    migratecfg.migrate()

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToSickBeard %s", VERSION)

# SABnzbd
if len(sys.argv) == SABNZB_NO_OF_ARGUMENTS:
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
elif len(sys.argv) == NZBGET_NO_OF_ARGUMENTS:
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
