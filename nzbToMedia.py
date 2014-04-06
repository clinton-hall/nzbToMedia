#!/usr/bin/env python

# adds lib directory to system path
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib')))

#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to CouchPotato, SickBeard, Mylar, Gamez, HeadPhones.
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
import logging
from nzbtomedia.autoProcess.autoProcessComics import autoProcessComics
from nzbtomedia.autoProcess.autoProcessGames import autoProcessGames
from nzbtomedia.autoProcess.autoProcessMovie import autoProcessMovie
from nzbtomedia.autoProcess.autoProcessMusic import autoProcessMusic
from nzbtomedia.autoProcess.autoProcessTV import autoProcessTV
from nzbtomedia.migratecfg import migratecfg
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaUtil import nzbtomedia_configure_logging, WakeUp, get_dirnames

# post-processing
def process(nzbDir, inputName=None, status=0, clientAgent='manual', download_id=None, inputCategory=None):
    if inputCategory in sections["CouchPotato"]:
        if isinstance(nzbDir, list):
            for dirName in nzbDir:
                Logger.info("MAIN: Calling CouchPotatoServer to post-process: %s", inputName)
                result =  autoProcessMovie().process(dirName, dirName, status, clientAgent, download_id, inputCategory)
                if result != 0:
                    return result
        else:
            Logger.info("MAIN: Calling CouchPotatoServer to post-process: %s", inputName)
            return autoProcessMovie().process(nzbDir, inputName, status, clientAgent, download_id, inputCategory)
    elif inputCategory in sections["SickBeard"]:
        if isinstance(nzbDir, list):
            for dirName in nzbDir:
                Logger.info("MAIN: Calling Sick-Beard to post-process: %s", inputName)
                result = autoProcessTV().processEpisode(dirName, dirName, status, clientAgent, inputCategory)
                if result !=0:
                    return result
        else:
            Logger.info("MAIN: Calling Sick-Beard to post-process: %s", inputName)
            return autoProcessTV().processEpisode(nzbDir, inputName, status, clientAgent, inputCategory)
    elif inputCategory in sections["HeadPhones"]:
        if isinstance(nzbDir, list):
            for dirName in nzbDir:
                Logger.info("MAIN: Calling Headphones to post-process: %s", dirName)
                result = autoProcessMusic().process(dirName, dirName, status, clientAgent, inputCategory)
                if result != 0:
                    return result
        else:
            Logger.info("MAIN: Calling HeadPhones to post-process: %s", inputName)
            return autoProcessMusic().process(nzbDir, inputName, status, clientAgent, inputCategory)
    elif inputCategory in sections["Mylar"]:
        if isinstance(nzbDir, list):
            for dirName in nzbDir:
                Logger.info("MAIN: Calling Mylar to post-process: %s", dirName)
                result = autoProcessComics().processEpisode(dirName, dirName, status, clientAgent, inputCategory)
                if result != 0:
                    return result
        else:
            Logger.info("MAIN: Calling Mylar to post-process: %s", inputName)
            return autoProcessComics().processEpisode(nzbDir, inputName, status, clientAgent, inputCategory)
    elif inputCategory in sections["Gamez"]:
        if isinstance(nzbDir, list):
            for dirName in nzbDir:
                Logger.info("MAIN: Calling Gamez to post-process: %s", dirName)
                result = autoProcessGames().process(dirName, dirName, status, clientAgent, inputCategory)
                if result != 0:
                    return result
        else:
            Logger.info("MAIN: Calling Gamez to post-process: %s", inputName)
            return autoProcessGames().process(nzbDir, inputName, status, clientAgent, inputCategory)
    else:
        Logger.warning("MAIN: The download category %s does not match any category defined in autoProcessMedia.cfg. Exiting.", inputCategory)
        return -1

########################################################################################################################

# run migrate to convert old cfg to new style cfg plus fix any cfg missing values/options.
if migratecfg().migrate():
    # check to write settings from nzbGet UI to autoProcessMedia.cfg.
    if os.environ.has_key('NZBOP_SCRIPTDIR'):
        migratecfg().addnzbget()

    nzbtomedia_configure_logging(config.LOG_FILE)

    Logger = logging.getLogger()
    Logger.info("====================")  # Seperate old from new log
    Logger.info("nzbToMedia %s", config.NZBTOMEDIA_VERSION)

    Logger.info("MAIN: Loading config from %s", config.CONFIG_FILE)
else:
    print("Unable to find " + config.CONFIG_FILE + " or " + config.SAMPLE_CONFIG_FILE)
    sys.exit(-1)

# setup sections and categories
sections = config.get_categories(["CouchPotato","SickBeard","HeadPhones","Mylar","Gamez"])

WakeUp()

# Post-Processing Result
result = 0

# NZBGet V11+
# Check if the script is called from nzbget 11.0 or later
if os.environ.has_key('NZBOP_SCRIPTDIR') and not os.environ['NZBOP_VERSION'][0:5] < '11.0':
    Logger.info("MAIN: Script triggered from NZBGet (11.0 or later).")

    # NZBGet argv: all passed as environment variables.
    clientAgent = "nzbget"

    # Check nzbget.conf options
    status = 0

    if os.environ['NZBOP_UNPACK'] != 'yes':
        Logger.error("MAIN: Please enable option \"Unpack\" in nzbget configuration file, exiting")
        sys.exit(config.NZBGET_POSTPROCESS_ERROR)

    # Check par status
    if os.environ['NZBPP_PARSTATUS'] == '3':
        Logger.warning("MAIN: Par-check successful, but Par-repair disabled, exiting")
        Logger.info("MAIN: Please check your Par-repair settings for future downloads.")
        sys.exit(config.NZBGET_POSTPROCESS_NONE)

    if os.environ['NZBPP_PARSTATUS'] == '1' or os.environ['NZBPP_PARSTATUS'] == '4':
        Logger.warning("MAIN: Par-repair failed, setting status \"failed\"")
        status = 1

    # Check unpack status
    if os.environ['NZBPP_UNPACKSTATUS'] == '1':
        Logger.warning("MAIN: Unpack failed, setting status \"failed\"")
        status = 1

    if os.environ['NZBPP_UNPACKSTATUS'] == '0' and os.environ['NZBPP_PARSTATUS'] == '0':
        # Unpack was skipped due to nzb-file properties or due to errors during par-check

        if os.environ['NZBPP_HEALTH'] < 1000:
            Logger.warning("MAIN: Download health is compromised and Par-check/repair disabled or no .par2 files found. Setting status \"failed\"")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")
            status = 1

        else:
            Logger.info("MAIN: Par-check/repair disabled or no .par2 files found, and Unpack not required. Health is ok so handle as though download successful")
            Logger.info("MAIN: Please check your Par-check/repair settings for future downloads.")

    # Check if destination directory exists (important for reprocessing of history items)
    if not os.path.isdir(os.environ['NZBPP_DIRECTORY']):
        Logger.error("MAIN: Nothing to post-process: destination directory %s doesn't exist. Setting status \"failed\"", os.environ['NZBPP_DIRECTORY'])
        status = 1

    # All checks done, now launching the script.
    download_id = ""
    if os.environ.has_key('NZBPR_COUCHPOTATO'):download_id = os.environ['NZBPR_COUCHPOTATO']
    result = process(os.environ['NZBPP_DIRECTORY'], inputName=os.environ['NZBPP_NZBFILENAME'], clientAgent = "nzbget", inputCategory=os.environ['NZBPP_CATEGORY'])
    if result != 0: Logger.info("MAIN: A problem was reported in the autoProcess* script.")
# SABnzbd Pre 0.7.17
elif len(sys.argv) == config.SABNZB_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    Logger.info("MAIN: Script triggered from SABnzbd")
    result = process(sys.argv[1], inputName=sys.argv[2], status=sys.argv[7], inputCategory=sys.argv[5], clientAgent = "sabnzbd", download_id='')
    if result != 0: Logger.info("MAIN: A problem was reported in the autoProcess* script.")
# SABnzbd 0.7.17+
elif len(sys.argv) >= config.SABNZB_0717_NO_OF_ARGUMENTS:
    # SABnzbd argv:
    # 1 The final directory of the job (full path)
    # 2 The original name of the NZB file
    # 3 Clean version of the job name (no path info and ".nzb" removed)
    # 4 Indexer's report number (if supported)
    # 5 User-defined category
    # 6 Group that the NZB was posted in e.g. alt.binaries.x
    # 7 Status of post processing. 0 = OK, 1=failed verification, 2=failed unpack, 3=1+2
    # 8 Failure URL
    Logger.info("MAIN: Script triggered from SABnzbd 0.7.17+")
    result = process(sys.argv[1], inputName=sys.argv[2], status=sys.argv[7], inputCategory=sys.argv[5], clientAgent = "sabnzbd", download_id='')
    if result != 0:Logger.info("MAIN: A problem was reported in the autoProcess* script.")
else:
    result = 0

    Logger.warn("MAIN: Invalid number of arguments received from client.")
    for section, categories in sections.items():
        for category in categories:
            dirnames = get_dirnames(section, category)
            Logger.info("MAIN: Running " + section + ":" + category + " as a manual run...")
            if process(dirnames, inputName=dirnames, status=0, inputCategory=category, clientAgent = "manual") != 0:
                Logger.info("MAIN: A problem was reported when trying to manually run " + section + ":" + category + ".")

if result == 0:
    Logger.info("MAIN: The nzbToMedia script completed successfully.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(config.NZBGET_POSTPROCESS_SUCCESS)
else:
    Logger.info("MAIN: A problem was reported in the nzbToMedia script.")
    if os.environ.has_key('NZBOP_SCRIPTDIR'): # return code for nzbget v11
        sys.exit(config.NZBGET_POSTPROCESS_ERROR)
