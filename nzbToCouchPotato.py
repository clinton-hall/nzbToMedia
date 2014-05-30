#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to CouchPotato, SickBeard, NzbDrone, Mylar, Gamez, HeadPhones.
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

# CouchPotato uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#cpsssl=0

# CouchPotato URL_Base
#
# set this if using a reverse proxy.
#cpsweb_root=

# CouchPotato watch directory.
#
# set this to where your CouchPotato completed downloads are.
#cpswatch_dir=

# CouchPotato Postprocess Method (renamer, manage).
#
# use "renamer" for CPS renamer (default) or "manage" to call a manage update.
#cpsmethod=renamer

# CouchPotato Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#cpsdelete_failed=0

# CouchPotato wait_for
#
# Set the number of minutes to wait after calling the renamer, to check the movie has changed status.
#cpswait_for=2

# CouchPotatoServer and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#cpsremote_path=0

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
import sys
import nzbToMedia

section = "CouchPotato"
result = nzbToMedia.main(sys.argv, section)
sys.exit(result)