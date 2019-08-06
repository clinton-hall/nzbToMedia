#!/usr/bin/env python
# coding=utf-8
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to LazyLibrarian.
#
# This script sends the download to your automated media management servers.
#
# NOTE: This script requires Python to be installed on your system.

##############################################################################
#
### OPTIONS                                                                ###

## General

# Auto Update nzbToMedia (0, 1).
#
# Set to 1 if you want nzbToMedia to automatically check for and update to the latest version
#auto_update=0

# Safe Mode protection of DestDir (0, 1).
#
# Enable/Disable a safety check to ensure we don't process all downloads in the default_downloadDirectory by mistake.
#safe_mode=1

## LazyLibrarian

# LazyLibrarian script category.
#
# category that gets called for post-processing with LazyLibrarian.
#llCategory=books

# LazyLibrarian api key.
#llapikey=

# LazyLibrarian host.
#
# The ipaddress for your LazyLibrarian server. e.g For the Same system use localhost or 127.0.0.1
#llhost=localhost

# LazyLibrarian port.
#llport=5299

# LazyLibrarian uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#llssl=0

# LazyLibrarian web_root
#
# set this if using a reverse proxy.
#llweb_root=

# LazyLibrarian watch directory.
#
# set this to where your LazyLibrarian completed downloads are.
#llwatch_dir=

# LazyLibrarian and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#llremote_path=0

## Network

# Network Mount Points (Needed for remote path above)
#
# Enter Mount points as LocalPath,RemotePath and separate each pair with '|'
# e.g. mountPoints=/volume1/Public/,E:\|/volume2/share/,\\NAS\
#mountPoints=

## Posix

# Niceness for external tasks Extractor and Transcoder.
#
# Set the Niceness value for the nice command. These range from -20 (most favorable to the process) to 19 (least favorable to the process). 
# If entering an integer e.g 'niceness=4', this is added to the nice command and passed as 'nice -n4' (Default). 
# If entering a comma separated list e.g. 'niceness=nice,4' this will be passed as 'nice 4' (Safer).
#niceness=nice,-n0

# ionice scheduling class (0, 1, 2, 3).
#
# Set the ionice scheduling class. 0 for none, 1 for real time, 2 for best-effort, 3 for idle.
#ionice_class=2

# ionice scheduling class data.
#
# Set the ionice scheduling class data. This defines the class data, if the class accepts an argument. For real time and best-effort, 0-7 is valid data.
#ionice_classdata=4

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

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import sys

import nzbToMedia

section = 'LazyLibrarian'
result = nzbToMedia.main(sys.argv, section)
sys.exit(result)
