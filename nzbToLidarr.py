#!/usr/bin/env python
# coding=utf-8
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to Lidarr.
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

## Lidarr

# Lidarr script category.
#
# category that gets called for post-processing with NzbDrone.
#liCategory=music2

# Lidarr host.
#
# The ipaddress for your Lidarr server. e.g For the Same system use localhost or 127.0.0.1
#lihost=localhost

# Lidarr port.
#liport=8686

# Lidarr API key.
#liapikey=

# Lidarr uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#lissl=0

# Lidarr web_root
#
# set this if using a reverse proxy.
#liweb_root=

# Lidarr wait_for
#
# Set the number of minutes to wait after calling the renamer, to check the episode has changed status.
#liwait_for=6

# Lidarr Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#lidelete_failed=0

# Lidarr and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#liremote_path=0

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
#mediaExtensions=.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso,.ts

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

## Transcoder

# getSubs (0, 1).
#
# set to 1 to download subtitles.
#getSubs = 0

# subLanguages.
#
# subLanguages. create a list of languages in the order you want them in your subtitles.
#subLanguages = eng,spa,fra

# Transcode (0, 1).
#
# set to 1 to transcode, otherwise set to 0.
#transcode=0

# create a duplicate, or replace the original (0, 1).
#
# set to 1 to cretae a new file or 0 to replace the original
#duplicate=1

# ignore extensions.
#
# list of extensions that won't be transcoded.
#ignoreExtensions=.avi,.mkv

# outputFastStart (0,1).
#
# outputFastStart. 1 will use -movflags + faststart. 0 will disable this from being used.
#outputFastStart = 0

# outputVideoPath.
#
# outputVideoPath. Set path you want transcoded videos moved to. Leave blank to disable.
#outputVideoPath =

# processOutput (0,1).
#
# processOutput. 1 will send the outputVideoPath to SickBeard/CouchPotato. 0 will send original files.
#processOutput = 0

# audioLanguage.
#
# audioLanguage. set the 3 letter language code you want as your primary audio track.
#audioLanguage = eng

# allAudioLanguages (0,1).
#
# allAudioLanguages. 1 will keep all audio tracks (uses AudioCodec3) where available.
#allAudioLanguages = 0

# allSubLanguages (0,1).
#
# allSubLanguages. 1 will keep all exisiting sub languages. 0 will discare those not in your list above.
#allSubLanguages = 0

# embedSubs (0,1).
#
# embedSubs. 1 will embded external sub/srt subs into your video if this is supported.
#embedSubs = 1

# burnInSubtitle (0,1).
#
# burnInSubtitle. burns the default sub language into your video (needed for players that don't support subs)
#burnInSubtitle = 0

# extractSubs (0,1).
#
# extractSubs. 1 will extract subs from the video file and save these as external srt files.
#extractSubs = 0

# externalSubDir.
#
# externalSubDir. set the directory where subs should be saved (if not the same directory as the video)
#externalSubDir =

# outputDefault (None, iPad, iPad-1080p, iPad-720p, Apple-TV2, iPod, iPhone, PS3, xbox, Roku-1080p, Roku-720p, Roku-480p, mkv, mkv-bluray, mp4-scene-release, MKV-SD).
#
# outputDefault. Loads default configs for the selected device. The remaining options below are ignored.
# If you want to use your own profile, set None and set the remaining options below.
#outputDefault = None

# hwAccel (0,1).
#
# hwAccel. 1 will set ffmpeg to enable hardware acceleration (this requires a recent ffmpeg).
#hwAccel=0

# ffmpeg output settings.
#outputVideoExtension=.mp4
#outputVideoCodec=libx264
#VideoCodecAllow =
#outputVideoResolution=720:-1
#outputVideoPreset=medium
#outputVideoFramerate=24
#outputVideoBitrate=800k
#outputAudioCodec=libmp3lame
#AudioCodecAllow =
#outputAudioBitrate=128k
#outputQualityPercent = 0
#outputAudioTrack2Codec = libfaac
#AudioCodec2Allow =
#outputAudioTrack2Bitrate = 128k
#outputAudioOtherCodec = libmp3lame
#AudioOtherCodecAllow =
#outputAudioOtherBitrate = 128k
#outputSubtitleCodec =

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

section = 'Lidarr'
result = nzbToMedia.main(sys.argv, section)
sys.exit(result)
