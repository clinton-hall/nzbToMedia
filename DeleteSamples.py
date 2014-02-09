#!/usr/bin/env python
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

import os
import sys


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

    # NZBGet argv: all passed as environment variables.
    clientAgent = "nzbget"
    # Exit codes used by NZBGet
    POSTPROCESS_PARCHECK=92
    POSTPROCESS_SUCCESS=93
    POSTPROCESS_ERROR=94
    POSTPROCESS_NONE=95

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        print "Please enable option \"Unpack\" in nzbget configuration file, exiting"
        sys.exit(POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        print "Par-check successful, but Par-repair disabled, exiting"
        sys.exit(POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1':
        print "Par-check failed, setting status \"failed\""
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        print "Unpack failed, setting status \"failed\""
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] != '2':
        # Unpack is disabled or was skipped due to nzb-file properties or due to errors during par-check

        for dirpath, dirnames, filenames in os.walk(os.environ['NZBPP_DIRECTORY']):
            for file in filenames:
                fileExtension = os.path.splitext(file)[1]

                if fileExtension in ['.rar', '.7z'] or os.path.splitext(fileExtension)[1] in ['.rar', '.7z']:
                    print "Post-Process: Archive files exist but unpack skipped, setting status \"failed\""
                    status = 1
                    break

                if fileExtension in ['.par2']:
                    print "Post-Process: Unpack skipped and par-check skipped (although par2-files exist), setting status \"failed\"g"
                    status = 1
                    break

        if os.path.isfile(os.path.join(os.environ['NZBPP_DIRECTORY'], "_brokenlog.txt")) and not status == 1:
            print "Post-Process: _brokenlog.txt exists, download is probably damaged, exiting"
            status = 1

        if not status == 1:
            print "Neither archive- nor par2-files found, _brokenlog.txt doesn't exist, considering download successful"

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        print "Post-Process: Nothing to post-process: destination directory ", os.environ['NZBPP_DIRECTORY'], "doesn't exist"
        status = 1

    # All checks done, now launching the script.

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
                        sys.exit(POSTPROCESS_ERROR)
    sys.exit(POSTPROCESS_SUCCESS)

else:
    print "This script can only be called from NZBGet (11.0 or later)."
    sys.exit(0)
