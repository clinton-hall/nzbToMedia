#!/usr/bin/env python

# adds lib directory to system path
import os
import sys
from nzbtomedia.nzbToMediaConfig import config

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib')))

#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Delete ".sample" files.
#
# This script removed sample files from the download directory.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

# Media Extensions
#
# This is a list of media extensions that may be deleted if a Sample_id is in the filename.
#mediaExtensions=.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso

# maxSampleSize
#
# This is the maximum size (in MiB) to be be considered as sample file.
#maxSampleSize=200

# SampleIDs
#
# This is a list of identifiers used for samples. e.g sample,-s. Use 'SizeOnly' to delete all media files less than maxSampleSize.
#SampleIDs=sample,-s. 

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

def is_sample(filePath, inputName, maxSampleSize, SampleIDs):
    # 200 MB in bytes
    SIZE_CUTOFF = int(maxSampleSize) * 1024 * 1024
    if os.path.getsize(filePath) < SIZE_CUTOFF:
        if 'SizeOnly' in SampleIDs:
            return True
        # Ignore 'sample' in files unless 'sample' in Torrent Name
        for ident in SampleIDs:
            if ident.lower() in filePath.lower() and not ident.lower() in inputName.lower(): 
                return True
    # Return False if none of these were met.
    return False


# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
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

    mediaContainer = os.environ['NZBPO_MEDIAEXTENSIONS'].split(',')
    SampleIDs = os.environ['NZBPO_SAMPLEIDS'].split(',')
    for dirpath, dirnames, filenames in os.walk(os.environ['NZBPP_DIRECTORY']):
        for file in filenames:

            filePath = os.path.join(dirpath, file)
            fileName, fileExtension = os.path.splitext(file)

            if fileExtension in mediaContainer:  # If the file is a video file
                if is_sample(filePath, os.environ['NZBPP_NZBNAME'], os.environ['NZBPO_MAXSAMPLESIZE'], SampleIDs):  # Ignore samples
                    print "Deleting sample file: ", filePath
                    try:
                        os.unlink(filePath)
                    except:
                        print "Error: unable to delete file", filePath
                        sys.exit(config.POSTPROCESS_ERROR)
    sys.exit(config.POSTPROCESS_SUCCESS)

else:
    print "This script can only be called from NZBGet (11.0 or later)."
    sys.exit(0)
