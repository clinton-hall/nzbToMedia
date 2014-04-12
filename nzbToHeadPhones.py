#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to HeadPhones.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

## HeadPhones

# HeadPhones script category.
#
# category that gets called for post-processing with HeadHones.
#hpCategory=music

# HeadPhones api key.
#hpapikey=

# HeadPhones host.
#hphost=localhost

# HeadPhones port.
#hpport=8181

# HeadPhones uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#hpssl=0

# HeadPhones web_root
#
# set this if using a reverse proxy.
#hpweb_root=

# HeadPhones Postprocess Delay.
#
# set as required to ensure correct processing.
#hpdelay=65

# HeadPhones process Time Per GiB
#
# Set the number of seconds to wait, for each GiB of data, before timing out. If transfering files across drives or network, increase this value as needed.
#hpTimePerGiB=60

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
import nzbtomedia

from nzbtomedia.autoProcess.autoProcessMusic import autoProcessMusic
from nzbtomedia.nzbToMediaUtil import get_dirnames
from nzbtomedia import logger

# Initialize the config
nzbtomedia.initialize()

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    logger.postprocess("Script triggered from NZBGet (11.0 or later).")

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        logger.error("Please enable option \"Unpack\" in nzbget configuration file, exiting")
        sys.exit(nzbtomedia.NZBGET_POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        logger.warning("Par-check successful, but Par-repair disabled, exiting")
        logger.postprocess("Please check your Par-repair settings for future downloads.")
        sys.exit(nzbtomedia.NZBGET_POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        logger.warning("Par-repair failed, setting status \"failed\"")
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        logger.warning("Unpack failed, setting status \"failed\"")
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            logger.warning("Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"")
            logger.postprocess("Please check your Par-check/repair settings for future downloads.")
            status = 1

        else:
            logger.postprocess("Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful")
            logger.postprocess("Please check your Par-check/repair settings for future downloads.")

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        logger.error("Nothing to post-process: destination directory %s doesn't exist. Setting status \"failed\"", os.environ['NZBPP_DIRECTORY'])
        status = 1

    # All checks done, now launching the script.
    logger.postprocess("Script triggered from NZBGet, starting autoProcessMusic...")
    clientAgent = "nzbget"
    result = autoProcessMusic().process(os.environ['NZBPP_DIRECTORY'], os.environ['NZBPP_NZBFILENAME'], status, clientAgent, os.environ['NZBPP_CATEGORY'])
# SABnzbd Pre 0.7.17
elif len(sys.argv) == nzbtomedia.SABNZB_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    logger.postprocess("Script triggered from SABnzbd, starting autoProcessMusic...")
    clientAgent = "sabnzbd"
    result = autoProcessMusic().process(sys.argv[1], sys.argv[2], sys.argv[7], clientAgent, sys.argv[5])
# SABnzbd 0.7.17+
elif len(sys.argv) >= nzbtomedia.SABNZB_0717_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    # 8 Failue URL
    logger.postprocess("Script triggered from SABnzbd 0.7.17+, starting autoProcessMusic...")
    clientAgent = "sabnzbd"
    result = autoProcessMusic().process(sys.argv[1], sys.argv[2], sys.argv[7], clientAgent, sys.argv[5])
else:
    result = 0

    logger.warning("Invalid number of arguments received from client.")
    for section, subsection in nzbtomedia.SUBSECTIONS['HeadPhones'].items():
        for category in subsection:
            if nzbtomedia.CFG[section].isenabled(category):
                dirNames = get_dirnames(section, category)
                for dirName in dirNames:
                    logger.postprocess("nzbToHeadPhones running %s:%s as a manual run on folder %s ...", section, category, dirName)
                    results = autoProcessMusic().process(dirName, os.path.basename(dirName), 0, inputCategory=category)
                    if results != 0:
                        result = results
                        logger.error("A problem was reported when trying to manually run %s:%s on folder %s ...", section, category, dirName)
            else:
                logger.postprocess("nzbToHeadPhones %s:%s is DISABLED, you can enable this in autoProcessMedia.cfg ...", section, category)

if result == 0:
    logger.postprocess("The autoProcessMusic script completed successfully.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(nzbtomedia.NZBGET_POSTPROCESS_SUCCESS)
else:
    logger.error("A problem was reported in the autoProcessMusic script.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(nzbtomedia.NZBGET_POSTPROCESS_ERROR)

