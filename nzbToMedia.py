#!/usr/bin/env python
# coding=utf-8
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to CouchPotato, SickBeard, Sonarr, Mylar, Gamez, HeadPhones,
# LazyLibrarian, Radarr, Lidarr, Watcher3
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

# Required Language
#
# Required Audio Language for media to be deemed valid e.g. = eng will only accept a video as valid if it contains English audio. Leave blank to disregard.
#require_lan=

# Safe Mode protection of DestDir (0, 1).
#
# Enable/Disable a safety check to ensure we don't process all downloads in the default_downloadDirectory by mistake.
#safe_mode=1

# Disable additional extraction checks for failed (0, 1).
#
# Turn this on to disable additional extraction attempts for failed downloads. Default = 0 this will attempt to extract and verify if media is present.
#no_extract_failed = 0

## CouchPotato

# CouchPotato script category.
#
# category that gets called for post-processing with CouchPotatoServer.
#cpsCategory=movie

# CouchPotato api key.
#cpsapikey=

# CouchPotato host.
#
# The ipaddress for your CouchPotato server. e.g For the Same system use localhost or 127.0.0.1
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

# CouchPotato Postprocess Method (renamer, manage).
#
# use "renamer" for CPS renamer (default) or "manage" to call a manage update.
#cpsmethod=renamer

# CouchPotato OMDB API Key.
#
# api key for www.omdbapi.com (used as alternative to imdb to assist with movie identification).
#cpsomdbapikey=

# CouchPotato Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#cpsdelete_failed=0

# CouchPotato wait_for
#
# Set the number of minutes to wait after calling the renamer, to check the movie has changed status.
#cpswait_for=2

# Couchpotato and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#cpsremote_path=0

## Radarr

# Radarr script category.
#
# category that gets called for post-processing with NzbDrone.
#raCategory=movies2

# Radarr host.
#
# The ipaddress for your Radarr server. e.g For the Same system use localhost or 127.0.0.1
#rahost=localhost

# Radarr port.
#raport=7878

# Radarr API key.
#raapikey=

# Radarr uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#rassl=0

# Radarr web_root
#
# set this if using a reverse proxy.
#raweb_root=

# Radarr wait_for
#
# Set the number of minutes to wait after calling the renamer, to check the episode has changed status.
#rawait_for=6

# Radarr OMDB API Key.
#
# api key for www.omdbapi.com (used as alternative to imdb to assist with movie identification).
#raomdbapikey=

# Radarr import mode (Move, Copy).
#
# set to define import behaviour Move or Copy
#raimportmode=Copy

# Radarr Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#radelete_failed=0

# Radarr and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#raremote_path=0

## Watcher3

# Wather3 script category.
#
# category that gets called for post-processing with Watcher3.
#W3Category=movie

# Watcher3 api key.
#W3apikey=

# Watcher3 host.
#
# The ipaddress for your Watcher3 server. e.g For the Same system use localhost or 127.0.0.1
#W3host=localhost

# Watcher3 port.
#W3port=9090

# Watcher3 uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#W3ssl=0

# Watcher3 URL_Base
#
# set this if using a reverse proxy.
#W3web_root=

# OMDB API Key.
#
# api key for www.omdbapi.com (used as alternative to imdb to assist with movie identification).
#W3omdbapikey=

# Watcher3 Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#W3delete_failed=0

# Watcher3 wait_for
#
# Set the number of minutes to wait after calling the renamer, to check the movie has changed status.
#W3wait_for=2

# Watcher3 and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#W3remote_path=0

## SickBeard

# SickBeard script category.
#
# category that gets called for post-processing with SickBeard.
#sbCategory=tv

# SickBeard host.
#
# The ipaddress for your SickBeard/SickRage server. e.g For the Same system use localhost or 127.0.0.1
#sbhost=localhost

# SickBeard port.
#sbport=8081

# SickBeard api key. For SickChill, Medusa, SiCKRAGE only.
#sbapikey=

# SickBeard username.
#sbusername=

# SickBeard password.
#sbpassword=

# SickBeard uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#sbssl=0

# SickBeard web_root
#
# set this if using a reverse proxy.
#sbweb_root=

# SickBeard watch directory.
#
# set this if SickBeard and nzbGet are on different systems.
#sbwatch_dir=

# SickBeard fork.
#
# set to default or auto to auto-detect the custom fork type.
#sbfork=auto

# SickBeard Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#sbdelete_failed=0

# SickBeard Ignore associated subtitle check (0, 1).
#
# set to 1 to ignore subtitles check, or 0 to don't check.
#sbignore_subs=0

# SickBeard process method.
#
# set this to move, copy, hardlink, symlink as appropriate if you want to over-ride SB defaults. Leave blank to use SB default.
#sbprocess_method=

# SickBeard and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#sbremote_path=0

## NzbDrone

# NzbDrone script category.
#
# category that gets called for post-processing with NzbDrone.
#ndCategory=tv2

# NzbDrone host.
#
# The ipaddress for your NzbDrone/Sonarr server. e.g For the Same system use localhost or 127.0.0.1
#ndhost=localhost

# NzbDrone port.
#ndport=8989

# NzbDrone API key.
#ndapikey=

# NzbDrone uses SSL (0, 1).
#
# Set to 1 if using SSL, else set to 0.
#ndssl=0

# NzbDrone web root.
#
# set this if using a reverse proxy.
#ndweb_root=

# NzbDrone wait_for
#
# Set the number of minutes to wait after calling the renamer, to check the episode has changed status.
#ndwait_for=6

# NzbDrone import mode (Move, Copy).
#
# set to define import behaviour Move or Copy
#ndimportmode=Copy

# NzbDrone Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#nddelete_failed=0

# NzbDrone and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#ndremote_path=0

## HeadPhones

# HeadPhones script category.
#
# category that gets called for post-processing with HeadHones.
#hpCategory=music

# HeadPhones api key.
#hpapikey=

# HeadPhones host.
#
# The ipaddress for your HeadPhones server. e.g For the Same system use localhost or 127.0.0.1
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

# HeadPhones Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#hpdelete_failed=0

# HeadPhones and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#hpremote_path=0

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

## Mylar

# Mylar script category.
#
# category that gets called for post-processing with Mylar.
#myCategory=comics

# Mylar host.
#
# The ipaddress for your Mylar server. e.g For the Same system use localhost or 127.0.0.1
#myhost=localhost

# Mylar port.
#myport=8090

# Mylar api key.
#myapikey=

# Mylar uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#myssl=0

# Mylar web_root
#
# set this if using a reverse proxy.
#myweb_root=

# Mylar wait_for
#
# Set the number of minutes to wait after calling the force process, to check the issue has changed status.
#myswait_for=1

# Mylar and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#myremote_path=0

## Gamez

# Gamez script category.
#
# category that gets called for post-processing with Gamez.
#gzCategory=games

# Gamez api key.
#gzapikey=

# Gamez host.
#
# The ipaddress for your Gamez server. e.g For the Same system use localhost or 127.0.0.1
#gzhost=localhost

# Gamez port.
#gzport=8085

# Gamez uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#gzssl=0

# Gamez library
#
# move downloaded games here.
#gzlibrary

# Gamez web_root
#
# set this if using a reverse proxy.
#gzweb_root=

# Gamez and NZBGet are a different system (0, 1).
#
# Enable to replace local path with the path as per the mountPoints below.
#gzremote_path=0

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
#getSubs=0

# subLanguages.
#
# subLanguages. create a list of languages in the order you want them in your subtitles.
#subLanguages=eng,spa,fra

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
#outputFastStart=0

# outputVideoPath.
#
# outputVideoPath. Set path you want transcoded videos moved to. Leave blank to disable.
#outputVideoPath=

# processOutput (0,1).
#
# processOutput. 1 will send the outputVideoPath to SickBeard/CouchPotato. 0 will send original files.
#processOutput=0

# audioLanguage.
#
# audioLanguage. set the 3 letter language code you want as your primary audio track.
#audioLanguage=eng

# allAudioLanguages (0,1).
#
# allAudioLanguages. 1 will keep all audio tracks (uses AudioCodec3) where available.
#allAudioLanguages=0

# allSubLanguages (0,1).
#
# allSubLanguages. 1 will keep all exisiting sub languages. 0 will discare those not in your list above.
#allSubLanguages=0

# embedSubs (0,1).
#
# embedSubs. 1 will embded external sub/srt subs into your video if this is supported.
#embedSubs=1

# burnInSubtitle (0,1).
#
# burnInSubtitle. burns the default sub language into your video (needed for players that don't support subs)
#burnInSubtitle=0

# extractSubs (0,1).
#
# extractSubs. 1 will extract subs from the video file and save these as external srt files.
#extractSubs=0

# externalSubDir.
#
# externalSubDir. set the directory where subs should be saved (if not the same directory as the video)
#externalSubDir=

# outputDefault (None, iPad, iPad-1080p, iPad-720p, Apple-TV2, iPod, iPhone, PS3, xbox, Roku-1080p, Roku-720p, Roku-480p, mkv, mkv-bluray, mp4-scene-release).
#
# outputDefault. Loads default configs for the selected device. The remaining options below are ignored.
# If you want to use your own profile, set None and set the remaining options below.
#outputDefault=None

# hwAccel (0,1).
#
# hwAccel. 1 will set ffmpeg to enable hardware acceleration (this requires a recent ffmpeg).
#hwAccel=0

# ffmpeg output settings.
#outputVideoExtension=.mp4
#outputVideoCodec=libx264
#VideoCodecAllow=
#outputVideoResolution=720:-1
#outputVideoPreset=medium
#outputVideoFramerate=24
#outputVideoBitrate=800k
#outputAudioCodec=ac3
#AudioCodecAllow=
#outputAudioChannels=6
#outputAudioBitrate=640k
#outputQualityPercent=
#outputAudioTrack2Codec=libfaac
#AudioCodec2Allow=
#outputAudioTrack2Channels=2
#outputAudioTrack2Bitrate=160k
#outputAudioOtherCodec=libmp3lame
#AudioOtherCodecAllow=
#outputAudioOtherChannels=2
#outputAudioOtherBitrate=128k
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

## UserScript

# User Script category.
#
# category that gets called for post-processing with user script (accepts "UNCAT", "ALL", or a defined category).
#usCategory=mine

# User Script Remote Path (0,1).
#
# Script calls commands on another system.
#usremote_path=0

# User Script extensions.
#
# What extension do you want to process? Specify all the extension, or use "ALL" to process all files.
#user_script_mediaExtensions=.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg

# User Script Path
#
# Specify the path to your custom script.
#user_script_path=/nzbToMedia/userscripts/script.sh

# User Script arguments.
#
# Specify the argument(s) passed to script, comma separated in order.
# for example FP,FN,DN, TN, TL for file path (absolute file name with path), file name, absolute directory name (with path), Torrent Name, Torrent Label/Category.
# So the result is /media/test/script/script.sh FP FN DN TN TL. Add other arguments as needed eg -f, -r
#user_script_param=FN

# User Script Run Once (0,1).
#
# Set user_script_runOnce = 0 to run for each file, or 1 to only run once (presumably on teh entire directory).
#user_script_runOnce=0

# User Script Success Codes.
#
# Specify the successcodes returned by the user script as a comma separated list. Linux default is 0
#user_script_successCodes=0

# User Script Clean After (0,1).
#
# Clean after? Note that delay function is used to prevent possible mistake :) Delay is intended as seconds
#user_script_clean=1

# User Script Delay.
#
# Delay in seconds after processing.
#usdelay=120

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
import sys

import eol
import cleanup

eol.check()
cleanup.clean(cleanup.FOLDER_STRUCTURE)

import core
from core import logger
from core.processor import nzbget, sab, manual
from core.processor.nzb import process
from core.auto_process.common import ProcessResult


def main(args, section=None):
    # Initialize the config
    core.initialize(section)

    logger.info('#########################################################')
    logger.info('## ..::[{0}]::.. ##'.format(os.path.basename(__file__)))
    logger.info('#########################################################')

    # debug command line options
    logger.debug('Options passed into nzbToMedia: {0}'.format(args))

    # Post-Processing Result
    result = ProcessResult(
        message='',
        status_code=0,
    )

    # NZBGet
    if 'NZBOP_SCRIPTDIR' in os.environ:
        result = nzbget.process()
    # SABnzbd
    elif 'SAB_SCRIPT' in os.environ:
        result = sab.process_script()
    # SABnzbd Pre 0.7.17
    elif len(args) >= sab.MINIMUM_ARGUMENTS:
        result = sab.process(args)
    # Generic program
    elif len(args) > 5 and args[5] == 'generic':
        logger.info('Script triggered from generic program')
        result = process(args[1], input_name=args[2], input_category=args[3], download_id=args[4])
    elif core.NZB_NO_MANUAL:
        logger.warning('Invalid number of arguments received from client, and no_manual set')
    else:
        manual.process()

    if result.status_code == 0:
        logger.info('The {0} script completed successfully.'.format(args[0]))
        if result.message:
            print(result.message + '!')
        if 'NZBOP_SCRIPTDIR' in os.environ:  # return code for nzbget v11
            del core.MYAPP
            return core.NZBGET_POSTPROCESS_SUCCESS
    else:
        logger.error('A problem was reported in the {0} script.'.format(args[0]))
        if result.message:
            print(result.message + '!')
        if 'NZBOP_SCRIPTDIR' in os.environ:  # return code for nzbget v11
            del core.MYAPP
            return core.NZBGET_POSTPROCESS_ERROR
    del core.MYAPP
    return result.status_code


if __name__ == '__main__':
    exit(main(sys.argv))
