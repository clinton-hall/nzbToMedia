#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to CouchPotato.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

## CouchPotato

# CouchPotato script category.
#
# category that gets called for post-processing with CouchPotatoServer.
#cpsCategory=movie

# CouchPotato api key.
#cpsapikey=

# CouchPotato host.
#cpshost=localhost

# CouchPotato port.
#cpsport=5050

# CouchPotato username.
#cpsusername= 

# CouchPotato password.
#cpspassword=

# CouchPotato uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#cpsssl=0

# CouchPotato URL_Base
#
# set this if using a reverse proxy.
#cpsweb_root=

# CouchPotato Postprocess Delay.
#
# must be at least 60 seconds.
#cpsdelay=65

# CouchPotato Postprocess Method (renamer, manage).
#
# use "renamer" for CPS renamer (default) or "manage" to call a manage update.
#cpsmethod=renamer

# CouchPotato Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#cpsdelete_failed=0

## Extensions

# Media Extensions
#
# This is a list of media extensions that may be transcoded if transcoder is enabled below.
#mediaExtensions=.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso

## Transcoder

# Transcode (0, 1).
#
# set to 1 to transcode, otherwise set to 0.
#transcode=0

# create a duplicate, or replace the original (0, 1).
#
# set to 1 to cretae a new file or 0 to replace the original
#duplicate=1

# ignore extensions
#
# list of extensions that won't be transcoded. 
#ignoreExtensions=.avi,.mkv

# ffmpeg output settings.
#outputVideoExtension=.mp4
#outputVideoCodec=libx264
#outputVideoPreset=medium
#outputVideoFramerate=24
#outputVideoBitrate=800k
#outputAudioCodec=libmp3lame
#outputAudioBitrate=128k
#outputSubtitleCodec=

## WakeOnLan

# use WOL (0, 1).
#
# set to 1 to send WOL broadcast to the mac and test the server (e.g. xbmc) on the host and port specified.
#wolwake=0

# WOL MAC
#
# enter the mac address of the system to be woken.
#wolmac=00:01:2e:2D:64:e1

# Set the Host and Port of a server to verify system has woken.
#wolhost=192.168.1.37
#wolport=80

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

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
# check to write settings from nzbGet UI to autoProcessMedia.cfg.
if os.environ.has_key('NZBOP_SCRIPTDIR'):
    migratecfg.addnzbget()

nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)

Logger.info("====================") # Seperate old from new log
Logger.info("nzbToCouchPotato %s", VERSION)

WakeUp()

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    Logger.info("MAIN: Script triggered from NZBGet (11.0 or later).")

    # NZBGet argv: all passed as environment variables.
    clientAgent = "nzbget"
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != "yes":
        Logger.error("Please enable option \"Unpack\" in nzbget configuration file, exiting")
        sys.exit(POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == 3:
        Logger.warning("Par-check successful, but Par-repair disabled, exiting")
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == 1:
        Logger.warning("Par-check failed, setting status \"failed\"")
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == 1:
        Logger.warning("Unpack failed, setting status \"failed\"")
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == 0 and os.environ['NZBPP_PARSTATUS'] != 2:
        # Unpack is disabled or was skipped due to nzb-file properties or due to errors during par-check

        for dirpath, dirnames, filenames in os.walk(os.environ['NZBPP_DIRECTORY']):
            for file in filenames:
                fileExtension = os.path.splitext(file)[1]

                if fileExtension in ['.rar', '.7z'] or os.path.splitext(fileExtension)[1] in ['.rar', '.7z']:
                    Logger.warning("Post-Process: Archive files exist but unpack skipped, exiting")
                    sys.exit(POSTPROCESS_NONE)

                if fileExtension in ['.par2']:
                    Logger.warning("Post-Process: Unpack skipped and par-check skipped (although par2-files exist), exiting")
                    sys.exit(POSTPROCESS_NONE)

        if os.path.isfile(os.path.join(os.environ['NZBPP_DIRECTORY'], "_brokenlog.txt")):
            Logger.warning("Post-Process: _brokenlog.txt exists, download is probably damaged, exiting")
            sys.exit(POSTPROCESS_NONE)

        Logger.info("Neither archive- nor par2-files found, _brokenlog.txt doesn't exist, considering download successful")

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        Logger.error("Post-Process: Nothing to post-process: destination directory %s doesn't exist", os.environ['NZBPP_DIRECTORY'])
        status = 1

    # All checks done, now launching the script.
    download_id = ""
    if os.environ.has_key('NZBPR_COUCHPOTATO'):
        download_id = os.environ['NZBPR_COUCHPOTATO']
    Logger.info("Script triggered from NZBGet, starting autoProcessMovie...")
    clientAgent = "nzbget"
    result = autoProcessMovie.process(os.environ['NZBPP_DIRECTORY'], os.environ['NZBPP_NZBNAME'], status, clientAgent, download_id)
# SABnzbd
elif len(sys.argv) == SABNZB_NO_OF_ARGUMENTS:
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
# NZBGet V10 or earlier
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

if result == 0:
    Logger.info("MAIN: The autoProcessMovie script completed successfully.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_SUCCESS)
else:
    Logger.info("MAIN: A problem was reported in the autoProcessMovie script.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(POSTPROCESS_ERROR)
