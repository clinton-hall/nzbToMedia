#!/usr/bin/env python

# adds lib directory to system path
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib')))

from nzbtomedia.nzbToMediaConfig import config

#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Reset the Date Modified and Date Created for downlaoded files.
#
# This is useful for sorting "newly added" media.
# This should run before other scripts.
#
# NOTE: This script requires Python to be installed on your system.

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    print "Script triggered from NZBGet (11.0 or later)."

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        print "Please enable option \"Unpack\" in nzbget configuration file, exiting."
        sys.exit(config.POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        print "Par-check successful, but Par-repair disabled, exiting."
        print "Please check your Par-repair settings for future downloads."
        sys.exit(config.POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        print "Par-repair failed, setting status \"failed\"."
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        print "Unpack failed, setting status \"failed\"."
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            print "Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"."
            print "Please check your Par-check/repair settings for future downloads."
            status = 1

        else:
            print "Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful."
            print "Please check your Par-check/repair settings for future downloads."

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        print "Nothing to post-process: destination directory", os.environ['NZBPP_DIRECTORY'], "doesn't exist. Setting status \"failed\"."
        status = 1

    # All checks done, now launching the script.

    if status == 1:
        sys.exit(config.POSTPROCESS_NONE)

    directory = os.path.normpath(os.environ['NZBPP_DIRECTORY'])
    for dirpath, dirnames, filenames in os.walk(directory):
        for file in filenames:
            filepath = os.path.join(dirpath, file)
            print "reseting datetime for file", filepath
            try:
                os.utime(filepath, None)
                continue
            except:
                print "Error: unable to reset time for file", file
                sys.exit(config.POSTPROCESS_ERROR)
    sys.exit(config.POSTPROCESS_SUCCESS)

else:
    print "This script can only be called from NZBGet (11.0 or later)."
    sys.exit(0)
