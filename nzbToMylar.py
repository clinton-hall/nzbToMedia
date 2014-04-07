#!/usr/bin/env python

# adds lib directory to system path
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib')))

#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to Mylar.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

## Mylar

# Mylar script category.
#
# category that gets called for post-processing with Mylar.
#myCategory=comics

# Mylar host.
#myhost=localhost

# Mylar port.
#myport=8090

# Mylar username.
#myusername= 

# Mylar password.
#mypassword=

# Mylar uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#myssl=0

# Mylar web_root
#
# set this if using a reverse proxy.
#myweb_root=

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

# Exit codes used by NZBGet
import logging
from nzbtomedia.autoProcess.autoProcessComics import autoProcessComics
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaUtil import nzbtomedia_configure_logging, WakeUp, get_dirnames

# run migrate to convert old cfg to new style cfg plus fix any cfg missing values/options.
if config().migrate():
    # check to write settings from nzbGet UI to autoProcessMedia.cfg.
    if os.environ.has_key('NZBOP_SCRIPTDIR'):
        config().addnzbget()

    nzbtomedia_configure_logging(config.LOG_FILE)
    Logger = logging.getLogger(__name__)
    Logger.info("====================")  # Seperate old from new log
    Logger.info("nzbToMylar %s", config.NZBTOMEDIA_VERSION)

    Logger.info("MAIN: Loading config from %s", config.CONFIG_FILE)
else:
    sys.exit(-1)

WakeUp()

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    Logger.info("MAIN: Script triggered from NZBGet (11.0 or later).")

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        Logger.error("MAIN: Please enable option \"Unpack\" in nzbget configuration file, exiting")
        sys.exit(config.NZBGET_POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        Logger.warning("MAIN: Par-check successful, but Par-repair disabled, exiting")
        Logger.info("MAIN: Please check your Par-repair settings for future downloads.")
        sys.exit(config.NZBGET_POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        Logger.warning("MAIN: Par-repair failed, setting status \"failed\"")
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        Logger.warning("MAIN: Unpack failed, setting status \"failed\"")
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            Logger.warning("MAIN: Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")
            status = 1

        else:
            Logger.info("MAIN: Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        Logger.error("MAIN: Nothing to post-process: destination directory %s doesn't exist. Setting status \"failed\"", os.environ['NZBPP_DIRECTORY'])
        status = 1

    # All checks done, now launching the script.
    Logger.info("MAIN: Script triggered from NZBGet, starting autoProcessComics...")
    result = autoProcessComics().processEpisode(os.environ['NZBPP_DIRECTORY'], os.environ['NZBPP_NZBNAME'], status)
# SABnzbd Pre 0.7.17
elif len(sys.argv) == config.SABNZB_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    Logger.info("MAIN: Script triggered from SABnzbd, starting autoProcessComics...")
    result = autoProcessComics().processEpisode(sys.argv[1], sys.argv[3], sys.argv[7])
# SABnzbd 0.7.17+
elif len(sys.argv) >= config.SABNZB_0717_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    # 8 Failure URL
    Logger.info("MAIN: Script triggered from SABnzbd 0.7.17+, starting autoProcessComics...")
    result = autoProcessComics().processEpisode(sys.argv[1], sys.argv[3], sys.argv[7])
else:
    result = 0

    # init sub-sections
    subsections = config().get_subsections(["Mylar"])

    Logger.warn("MAIN: Invalid number of arguments received from client.")
    for section, subsection in subsections.items():
        for category in subsection:
            if config().isenabled(section, category):
                dirNames = get_dirnames(section, category)
                for dirName in dirNames:
                    Logger.info("MAIN: nzbToMylar running %s:%s as a manual run...", section, category)
                    results = autoProcessComics().processEpisode(dirName, os.path.basename(dirName), 0, inputCategory=category)
                    if results != 0:
                        result = results
                        Logger.info("MAIN: A problem was reported when trying to manually run %s:%s.", section, category)
            else:
                Logger.info("MAIN: nzbTo%s %s:%s is DISABLED, you can enable this in autoProcessMedia.cfg ...", section, section, category)

if result == 0:
    Logger.info("MAIN: The autoProcessComics script completed successfully.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(config.NZBGET_POSTPROCESS_SUCCESS)
else:
    Logger.info("MAIN: A problem was reported in the autoProcessComics script.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(config.NZBGET_POSTPROCESS_ERROR)
