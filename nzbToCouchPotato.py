#!/usr/bin/env python

import os
import sys
import logging

import autoProcess.migratecfg as migratecfg
import autoProcess.autoProcessMovie as autoProcessMovie
from autoProcess.nzbToMediaEnv import *
from autoProcess.nzbToMediaUtil import *

#check to migrate old cfg before trying to load.
if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
    migratecfg.migrate()

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToCouchPotato %s", VERSION)

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
    Logger.info("Script triggered from SABnzbd, starting autoProcessMovie...")
    clientAgent = "sabnzbd"
    result = autoProcessMovie.process(sys.argv[1], sys.argv[2], sys.argv[7], clientAgent)
# NZBGet
elif len(sys.argv) == NZBGET_NO_OF_ARGUMENTS:
    # NZBGet argv:
    # 1  The final directory of the job (full path)
    # 2  The original name of the NZB file
    # 3  The status of the download: 0 == successful
    # 4  The category of the download:
    # 5  The download_id
    Logger.info("Script triggered from NZBGet, starting autoProcessMovie...")
    clientAgent = "nzbget"
    result = autoProcessMovie.process(sys.argv[1], sys.argv[2], sys.argv[3], clientAgent, sys.argv[5])
else:
    Logger.warn("Invalid number of arguments received from client.")
    Logger.info("Running autoProcessMovie as a manual run...")
    clientAgent = "manual"
    result = autoProcessMovie.process('Manual Run', 'Manual Run', 0, clientAgent)
