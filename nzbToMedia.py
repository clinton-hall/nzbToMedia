#!/usr/bin/env python

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]),'autoProcess/'))
import ConfigParser
import logging

import migratecfg
import autoProcessComics
import autoProcessGames 
import autoProcessMusic
import autoProcessTV
import autoProcessMovie
from nzbToMediaEnv import *
from nzbToMediaUtil import *

# check to migrate old cfg before trying to load.
if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
    migratecfg.migrate()

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToMedia %s", VERSION)
config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
if not os.path.isfile(configFilename):
    Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
    sys.exit(-1)
# CONFIG FILE
Logger.info("MAIN: Loading config from %s", configFilename)
config.read(configFilename)

cpsCategory = config.get("CouchPotato", "cpsCategory")                              # movie
sbCategory = config.get("SickBeard", "sbCategory")                                  # tv
hpCategory = config.get("HeadPhones", "hpCategory")                                 # music
mlCategory = config.get("Mylar", "mlCategory")                                      # comics
gzCategory = config.get("Gamez", "gzCategory")

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
    Logger.info("MAIN: Script triggered from SABnzbd")
    clientAgent = "sabnzbd"
    nzbDir, inputName, status, inputCategory, download_id = (sys.argv[1], sys.argv[2], sys.argv[7], sys.argv[5], '')
# NZBGet
elif len(sys.argv) == NZBGET_NO_OF_ARGUMENTS:
    # NZBGet argv:
    # 1  The final directory of the job (full path)
    # 2  The original name of the NZB file
    # 3  The status of the download: 0 == successful
    # 4  The category of the download:
    # 5  The download_id
    Logger.info("MAIN: Script triggered from NZBGet")
    clientAgent = "nzbget"
    nzbDir, inputName, status, inputCategory, download_id = (sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
else: # only CPS supports this manual run for now.
    Logger.warn("MAIN: Invalid number of arguments received from client.")
    Logger.info("MAIN: Running autoProcessMovie as a manual run...")
    clientAgent = "manual"
    nzbDir, inputName, status, inputCategory, download_id = ('Manual Run', 'Manual Run', 0, cpsCategory, '')

if inputCategory == cpsCategory:
    Logger.info("MAIN: Calling CouchPotatoServer to post-process: %s", inputName)
    result = autoProcessMovie.process(nzbDir, inputName, status, clientAgent, download_id)
elif inputCategory == sbCategory:
    Logger.info("MAIN: Calling Sick-Beard to post-process: %s", inputName)
    result = autoProcessTV.processEpisode(nzbDir, inputName, status)
elif inputCategory == hpCategory:
    Logger.info("MAIN: Calling HeadPhones to post-process: %s", inputName)
    result = autoProcessMusic.process(nzbDir, inputName, status)
elif inputCategory == mlCategory:
    Logger.info("MAIN: Calling Mylar to post-process: %s", inputName)
    result = autoProcessComics.processEpisode(nzbDir, inputName, status)
elif inputCategory == gzCategory:
    Logger.info("MAIN: Calling Gamez to post-process: %s", inputName)
    result = autoProcessGames.process(nzbDir, inputName, status)

if result == 0:
    Logger.info("MAIN: The autoProcess* script completed successfully.")
else:
    Logger.info("MAIN: A problem was reported in the autoProcess* script.")
