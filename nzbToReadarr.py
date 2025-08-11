#!/usr/bin/env python
# coding=utf-8
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to Readarr.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

## General

# Auto Update nzbToMedia (0, 1).
#
# Set to 1 if you want nzbToMedia to automatically check for and update to the latest version
#auto_update=0

# Check Media for corruption (0, 1).
#
# Enable/Disable media file checking using ffprobe.
#check_media=1

# Safe Mode protection of DestDir (0, 1).
#
# Enable/Disable a safety check to ensure we don't process all downloads in the default_downloadDirectory by mistake.
#safe_mode=1

# Disable additional extraction checks for failed (0, 1).
#
# Turn this on to disable additional extraction attempts for failed downloads. Default = 0 this will attempt to extract and verify if media is present.
#no_extract_failed = 0

## Readarr

# Readarr script category.
#
# category that gets called for post-processing with NzbDrone.
#raCategory=books

# Readarr host.
#
# The ipaddress for your Readarr server. e.g For the Same system use localhost or 127.0.0.1
#rahost=localhost

# Readarr port.
#raport=8787

# Readarr API key.
#raapikey=

# Readarr uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#rassl=0

# Readarr web_root
#
# set this if using a reverse proxy.
#raweb_root=

# Readarr wait_for
#
# Set the number of minutes to wait after calling the renamer, to check the episode has changed status.
#rawait_for=6

# Readarr import mode (Move, Copy).
#
# set to define import behaviour Move or Copy
#raimportmode=Copy

# Readarr Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#radelete_failed=0

# Readarr and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#raremote_path=0

## Network

# Network Mount Points (Needed for remote path above)
#
# Enter Mount points as LocalPath,RemotePath and separate each pair with '|'
# e.g. mountPoints=/volume1/Public/,E:\|/volume2/share/,\\NAS\
#mountPoints=

## Extensions

# Media Extensions
#
# This is a list of media extensions that are used to verify that the download does contain valid media.
#mediaExtensions=.epub,.azw3,.mobi,.pdf,.docx,.fb2,.htmlz,.lit,.lrf,.pdb,.pmlz,.rb,.rtf,.snb,.tcr,.txt,.txtz,.zip,.flac

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import sys

import nzbToMedia

section = 'Readarr'
result = nzbToMedia.main(sys.argv, section)
sys.exit(result)
