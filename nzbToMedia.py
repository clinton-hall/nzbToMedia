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

# CouchPotato Postprocess Delay.
#
# must be at least 60 seconds.
#cpsdelay=65

# CouchPotato Postprocess Method (renamer, manage).
#
# use "renamer" for CPS renamer (default) or "manage" to call a manage update.
#cpsmethod=renamer

# CouchPotato Delete Failed Downloads (0, 1).
#
# set to 1 to delete failed, or 0 to leave files in place.
#cpsdelete_failed=0

# CouchPotato process Time Per GiB
#
# Set the number of seconds to wait, for each GiB of data, before timing out. If transfering files across drives or network, increase this value as needed.
#cpsTimePerGiB=60

# CouchPotato wait_for
#
# Set the number of minutes to wait after calling the renamer, to check the movie has changed status.
#cpswait_for=2

# CouchPotatoServer and NZBGet are a different system (0, 1).
#
# set to 1 if CouchPotato and NZBGet are on a different system, or 0 if on the same system.
#remoteCPS = 0

## SickBeard

# SickBeard script category.
#
# category that gets called for post-processing with SickBeard.
#sbCategory=tv

# SickBeard host.
#sbhost=localhost

# SickBeard port.
#sbport=8081

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

# SickBeard delay
#
# Set the number of seconds to wait before calling post-process in SickBeard.
#sbdelay=0

# SickBeard process Time Per GiB
#
# Set the number of seconds to wait, for each GiB of data, before timing out. If transfering files across drives or network, increase this value as needed.
#sbTimePerGiB=60

# SickBeard watch directory.
#
# set this if SickBeard and nzbGet are on different systems.
#sbwatch_dir=

# SickBeard fork.
#
# set to default or auto to auto-detect the custom fork type.
#sbfork=auto

# SickBeard Delete Failed Downloads (0, 1)
#
# set to 1 to delete failed, or 0 to leave files in place.
#sbdelete_failed=0

# SickBeard process method.
#
# set this to move, copy, hardlin, symlink as appropriate if you want to over-ride SB defaults. Leave blank to use SB default.
#sbprocess_method=

## NzbDrone

# NzbDrone script category.
#
# category that gets called for post-processing with NzbDrone.
#ndCategory=tv

# NzbDrone host.
#ndHost=localhost

# NzbDrone port.
#ndPort=8989

# NzbDrone API key.
#ndAPIKey=

# NzbDrone uses SSL (0, 1).
#
# Set to 1 if using SSL, else set to 0.
#ndSSL=0

# NzbDrone web root.
#
# set this if using a reverse proxy.
#ndWebRoot=

# Prefer NzbDrone if categories clash (0, 1).
#ndPrefer=0

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

## Gamez

# Gamez script category.
#
# category that gets called for post-processing with Gamez.
#gzCategory=games

# Gamez api key.
#gzapikey=

# Gamez host.
#gzhost=localhost

# Gamez port.
#gzport=8085

# Gamez uses ssl (0, 1).
#
# Set to 1 if using ssl, else set to 0.
#gzssl=0

# Gamez web_root
#
# set this if using a reverse proxy.
#gzweb_root=

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
import os
import sys
import nzbtomedia
from nzbtomedia.autoProcess.autoProcessComics import autoProcessComics
from nzbtomedia.autoProcess.autoProcessGames import autoProcessGames
from nzbtomedia.autoProcess.autoProcessMovie import autoProcessMovie
from nzbtomedia.autoProcess.autoProcessMusic import autoProcessMusic
from nzbtomedia.autoProcess.autoProcessTV import autoProcessTV
from nzbtomedia.nzbToMediaUtil import get_dirnames
from nzbtomedia import logger

# post-processing
def process(nzbDir, inputName=None, status=0, clientAgent='manual', download_id=None, inputCategory=None):

    if nzbtomedia.CFG["CouchPotato"][inputCategory]:
        logger.postprocess("Calling CouchPotatoServer to post-process: %s", logger.MESSAGE), inputName
        return autoProcessMovie().process(nzbDir, inputName, status, clientAgent, download_id, inputCategory)
    elif nzbtomedia.CFG["SickBeard", "NzbDrone"][inputCategory]:
        logger.postprocess("Calling Sick-Beard to post-process: %s",logger.MESSAGE), inputName
        return autoProcessTV().processEpisode(nzbDir, inputName, status, clientAgent, inputCategory)
    elif nzbtomedia.CFG["HeadPhones"][inputCategory]:
        logger.postprocess("Calling HeadPhones to post-process: %s", logger.MESSAGE), inputName
        return autoProcessMusic().process(nzbDir, inputName, status, clientAgent, inputCategory)
    elif nzbtomedia.CFG["Mylar"][inputCategory]:
        logger.postprocess("Calling Mylar to post-process: %s",logger.MESSAGE), inputName
        return autoProcessComics().processEpisode(nzbDir, inputName, status, clientAgent, inputCategory)
    elif nzbtomedia.CFG["Gamez"][inputCategory]:
        logger.postprocess("Calling Gamez to post-process: %s",logger.MESSAGE), inputName
        return autoProcessGames().process(nzbDir, inputName, status, clientAgent, inputCategory)
    else:
        logger.postprocess("We could not find the section %s with a download category of %s in your autoProcessMedia.cfg. Exiting.",logger.WARNING), section, inputCategory
        return -1

########################################################################################################################
logger.postprocess("====================")  # Seperate old from new log
logger.postprocess("nzbToMedia %s", nzbtomedia.NZBTOMEDIA_VERSION)

logger.postprocess("Loading config from %s", nzbtomedia.CONFIG_FILE)

# Post-Processing Result
result = 0

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    logger.postprocess("Script triggered from NZBGet (11.0 or later).")

    # NZBGet argv: all passed as environment variables.
    clientAgent = "nzbget"

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
    download_id = ""
    if os.environ.has_key('NZBPR_COUCHPOTATO'):download_id = os.environ['NZBPR_COUCHPOTATO']
    result = process(os.environ['NZBPP_DIRECTORY'], inputName=os.environ['NZBPP_NZBFILENAME'], clientAgent = "nzbget", inputCategory=os.environ['NZBPP_CATEGORY'])
    if result != 0: logger.error("A problem was reported in the autoProcess* script.")
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
    logger.postprocess("Script triggered from SABnzbd")
    result = process(sys.argv[1], inputName=sys.argv[2], status=sys.argv[7], inputCategory=sys.argv[5], clientAgent = "sabnzbd", download_id='')
    if result != 0: logger.error("A problem was reported in the autoProcess* script.")
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
    # 8 Failure URL
    logger.postprocess("Script triggered from SABnzbd 0.7.17+")
    result = process(sys.argv[1], inputName=sys.argv[2], status=sys.argv[7], inputCategory=sys.argv[5], clientAgent = "sabnzbd", download_id='')
    if result != 0:logger.error("A problem was reported in the autoProcess* script.")
else:
    result = 0

    # init sub-sections
    logger.warning("Invalid number of arguments received from client.")
    for section, subsection in nzbtomedia.SUBSECTIONS.items():
        for category in subsection:
            if nzbtomedia.CFG[section][category].isenabled():
                dirNames = get_dirnames(section, category)
                for dirName in dirNames:
                    logger.postprocess("nzbToMedia running %s:%s as a manual run on folder %s ...", section, category, dirName)
                    results = process(dirName, os.path.basename(dirName), 0, inputCategory=category)
                    if results != 0:
                        result = results
                        logger.error("A problem was reported when trying to manually run %s:%s.", section, category)
            else:
                logger.postprocess("nzbToMedia %s:%s is DISABLED, you can enable this in autoProcessMedia.cfg ...", section, category)

if result == 0:
    logger.postprocess("The nzbToMedia script completed successfully.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(nzbtomedia.NZBGET_POSTPROCESS_SUCCESS)
else:
    logger.error("A problem was reported in the nzbToMedia script.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(nzbtomedia.NZBGET_POSTPROCESS_ERROR)
