#!/usr/bin/env python
#
# This file if part of nzbget
#
# Example postprocessing script for NZBGet
#
# Copyright (C) 2008 Peter Roubos <peterroubos@hotmail.com>
# Copyright (C) 2008 Otmar Werner
# Copyright (C) 2008-2013 Andrey Prygunkov <hugbug@users.sourceforge.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#
#######################    Usage instructions     #######################
# o  Script will cleanup, join ts-files and rename img-files to iso.
#
# o  To use this script with nzbget set the option "PostProcess" in
#    nzbget configuration file to point to this script file. E.g.:
#        PostProcess=/home/user/nzbget/nzbget-postprocess.sh
#
# o  The script needs a configuration file. An example configuration file
#    is provided in file "nzbget-postprocess.conf". Put the configuration file 
#    into the directory where nzbget's configuration file (nzbget.conf) is located.
#    Then edit the configuration file in any text editor to adjust the settings.
#
# o  You can also edit the script's configuration via web-interface.
#
# o  There are few options, which can be ajdusted for each nzb-file individually.
#
####################### End of Usage instructions #######################

import os
import logging
import logging.config
import sys
import shutil
from configobj import ConfigObj
from subprocess import call
from glob import iglob
import migratecfg
import autoProcessComics
import autoProcessGames 
import autoProcessMusic
import autoProcessTV
import autoProcessMovie

# Postprocessing function for nzbToCouchPotato and nzbToSickBeard
def nzbToMedia(nzbStatus):
    script = ""
    result = ""
    if Debug == "yes":
        Logger.debug("Post-Process: Executing external postprocessing with argument %s", nzbStatus) 
    PostProcessStatus = nzbStatus
    # 200 MB in bytes
    SIZE_CUTOFF = 200 * 1024 * 1024
    # Ignore 'sample' in files unless 'sample' in Torrent Name
    for dirpath, dirnames, filenames in os.walk(NZBPP_DIRECTORY):
                for file in filenames:
                    filePath = os.path.join(dirpath, file)
                    if ('sample' in filePath.lower()) and (not 'sample' in NZBPP_NZBNAME) and (os.path.getsize(filePath) < SIZE_CUTOFF):
                        Logger.info("Post-Process: Deleting sample file %s", filePath)
                        os.unlink(filePath)

    if NZBPP_CATEGORY == CouchPotatoCategory:
        if CouchPotato == "yes":
            script = "autoProcessMovie"
            # Call Couchpotato's postprocessing script
            Logger.info("Post-Process: Running CouchPotato's postprocessing script")

            if Debug == "yes":
                Logger.debug("Post-Process: CouchPotato-Script-ARGV1= %s", NZBPP_DIRECTORY)
                Logger.debug("Post-Process: CouchPotato-Script-ARGV2= %s", NZBPP_NZBFILENAME)
                Logger.debug("Post-Process: CouchPotato-Script-ARGV3= %s", PostProcessStatus)
            result = autoProcessMovie.process(NZBPP_DIRECTORY, NZBPP_NZBFILENAME, PostProcessStatus, clientAgent, download_id)
        else:
            Logger.debug("Post-Process: Ignored to run CouchPotato's postprocessing script as it is disabled by user")

    if NZBPP_CATEGORY == SickBeardCategory:
        if SickBeard == "yes":
            script = "autoProcessTv"
            # Call SickBeard's postprocessing script
            Logger.info("Post-Process: Running SickBeard's postprocessing script")

            if Debug == "yes":
                Logger.debug("Post-Process: SickBeard-Script-ARGV1= %s", NZBPP_DIRECTORY)
                Logger.debug("Post-Process: SickBeard-Script-ARGV2= %s", NZBPP_NZBFILENAME)
                Logger.debug("Post-Process: SickBeard-Script-ARGV3= %s", PostProcessStatus)
            result = autoProcessTV.processEpisode(NZBPP_DIRECTORY, NZBPP_NZBFILENAME, PostProcessStatus)
        else:
            Logger.debug("Post-Process: Ignored to run SickBeard's postprocessing script as it is disabled by user")

    if NZBPP_CATEGORY == HeadPhonesCategory:
        if HeadPhones == "yes":
            script = "autoProcessMusic"
            # Call HeadPhones' postprocessing script
            Logger.info("Post-Process: Running HeadPhones' postprocessing script")

            if Debug == "yes":
                Logger.debug("Post-Process: HeadPhones-Script-ARGV1= %s", NZBPP_DIRECTORY)
                Logger.debug("Post-Process: HeadPhones-Script-ARGV2= %s", NZBPP_NZBFILENAME)
                Logger.debug("Post-Process: HeadPhones-Script-ARGV3= %s", PostProcessStatus)
            result = autoProcessMusic.process(NZBPP_DIRECTORY, NZBPP_NZBFILENAME, PostProcessStatus)
        else:
            Logger.debug("Post-Process: Ignored to run HeadPhones' postprocessing script as it is disabled by user")

    if NZBPP_CATEGORY == MylarCategory:
        if Mylar == "yes":
            script = "autoProcessComics"
            # Call Mylar's postprocessing script
            Logger.info("Post-Process: Running Mylar's postprocessing script")

            if Debug == "yes":
                Logger.debug("Post-Process: Mylar-Script-ARGV1= %s", NZBPP_DIRECTORY)
                Logger.debug("Post-Process: Mylar-Script-ARGV2= %s", NZBPP_NZBFILENAME)
                Logger.debug("Post-Process: Mylar-Script-ARGV3= %s", PostProcessStatus)
            result = autoProcessComics.processEpisode(NZBPP_DIRECTORY, NZBPP_NZBFILENAME, PostProcessStatus)
        else:
            Logger.debug("Post-Process: Ignored to run Mylar's postprocessing script as it is disabled by user")

    if NZBPP_CATEGORY == GamezCategory:
        if Gamez == "yes":
            script = "autoProcessGames"
            # Call Gamez's postprocessing script
            Logger.info("Post-Process: Running Gamez's postprocessing script")

            if Debug == "yes":
                Logger.debug("Post-Process: Gamez-Script-ARGV1= %s", NZBPP_DIRECTORY)
                Logger.debug("Post-Process: Gamez-Script-ARGV2= %s", NZBPP_NZBFILENAME)
                Logger.debug("Post-Process: Gamez-Script-ARGV3= %s", PostProcessStatus)
            result = autoProcessGames.process(NZBPP_DIRECTORY, NZBPP_NZBFILENAME, PostProcessStatus)
        else:
            Logger.debug("Post-Process: Ignored to run Gamez's postprocessing script as it is disabled by user")

    return script, result

# Pass on postprocess exit codes to external scripts for handling failed downloads
def do_exit(Process_Code):
    if Debug == "yes":
        Logger.debug("Post-Process: Executing function 'do_exit' with argument %s", Process_Code)
    nzbStatus = 0
    if Process_Code != POSTPROCESS_SUCCESS: 
        if Delete_Failed == "yes":
            os.chdir(os.path.split(NZBPP_DIRECTORY)[0])
            shutil.rmtree(NZBPP_DIRECTORY)
        else:
            os.mkdir(Failed_Directory)
            os.chdir(Failed_Directory)
            for dirpath, dirnames, filenames in os.walk(NZBPP_DIRECTORY):
                for file in filenames:
                    filePath = os.path.join(dirpath, file)
                    newPath = os.path,join(Failed_Directory, file)
                    shutil.move(filePath, newPath)
            shutil.rmtree(NZBPP_DIRECTORY)
            NZBPP_DIRECTORY = Failed_Directory
            os.chdir(NZBPP_DIRECTORY)
        nzbStatus=1 
    script = "none"
    Email_Message2 = Email_Message
    script, result = nzbToMedia(nzbStatus)
    Logger.debug("after calling nzbToMedia")
    Email_Subject.replace("<name>", NZBPP_NZBFILENAME)
    Email_Subject.replace("<cat>", NZBPP_CATEGORY)
    Email_Subject.replace("<script>", script)
    Email_Message2.replace("<name>", NZBPP_NZBFILENAME)
    Email_Message2.replace("<cat>", NZBPP_CATEGORY)
    Email_Message2.replace("<script>", script)

    if NZBPP_CATEGORY in Email_successful and nzbStatus == 0:
        Email_Subject.replace("<status>", "completed")
        Email_Message2.replace("<status>", "completed")
        if Add_Log == "yes": 
            Email_Message2 = Email_Message2 + "\r\nLog Result"
            f = open(logFile2)
            lines = f.readlines()
            for line in lines:
                if line != "":
                    Email_Message2 = Email_Message2 + "\r\n" + line
            f.close()
        command = [sendEmail, "-f", Email_From, "-t", Email_To, "-s", Email_Server, "-o", "tls=" + Tls]
        if Email_User != "" and Email_Pass != "":
            command.append("-xu")
            command.append(Email_User)
            command.append("-xp")
            command.append(Email_Pass)
        command.append("-u")
        command.append(Email_Subject)
        command.append("-m")
        command.append(Email_Message2)
        call(command)

    if NZBPP_CATEGORY in Email_failed and nzbStatus != 0:
        Email_Subject.replace("<status>", "failed")
        Email_Message.replace("<status>", "failed")
        if Add_Log == "yes": 
            Email_Message2 = Email_Message2 + "\r\nLog Result"
            f = open(logFile2)
            lines = f.readlines()
            for line in lines:
                if line != "":
                    Email_Message2 = Email_Message2 + "\r\n" + line
            f.close()
        command = [sendEmail, "-f", Email_From, "-t", Email_To, "-s", Email_Server, "-o", "tls=" + Tls]
        if Email_User != "" and Email_Pass != "":
            command.append("-xu")
            command.append(Email_User)
            command.append("-xp")
            command.append(Email_Pass)
        command.append("-u")
        command.append(Email_Subject)
        command.append("-m")
        command.append(Email_Message2)
        call(command)
        
    exit(Process_Code)

if os.path.isfile(os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")):
    migratecfg.migrate()

logFile = os.path.join(os.path.dirname(sys.argv[0]), "postprocess.log")
logging.config.fileConfig(os.path.join(os.path.dirname(sys.argv[0]), "logging.cfg"))
fileHandler = logging.handlers.RotatingFileHandler(logFile, mode='a', maxBytes=20000, backupCount=1, encoding='utf-8', delay=True)
fileHandler.formatter = logging.Formatter('%(asctime)s|%(levelname)-7.7s %(message)s', '%H:%M:%S')
fileHandler.level = logging.DEBUG
logging.getLogger().addHandler(fileHandler)

logFile2 = os.path.join(os.path.dirname(sys.argv[0]), "tmp.log")
fileHandler2 = logging.FileHandler(logFile2, mode='w', encoding='utf-8', delay=True)
fileHandler2.formatter = logging.Formatter('%(asctime)s|%(levelname)-7.7s %(message)s', '%H:%M:%S')
fileHandler2.level = logging.DEBUG
logging.getLogger().addHandler(fileHandler2)

Logger = logging.getLogger(__name__)


# NZBGet passes following arguments to postprocess-programm as environment
# variables:
#  NZBPP_DIRECTORY    - path to destination dir for downloaded files;
NZBPP_DIRECTORY = os.path.normpath(os.getenv('NZBPP_DIRECTORY'))
#  NZBPP_NZBNAME      - user-friendly name of processed nzb-file as it is displayed
#                       by the program. The file path and extension are removed.
#                       If download was renamed, this parameter reflects the new name;
NZBPP_NZBNAME = os.getenv('NZBPP_NZBNAME')
#  NZBPP_NZBFILENAME  - name of processed nzb-file. It includes file extension and also
#                       may include full path;
NZBPP_NZBFILENAME = os.getenv('NZBPP_NZBFILENAME')
#  NZBPP_CATEGORY     - category assigned to nzb-file (can be empty string);
NZBPP_CATEGORY = os.getenv('NZBPP_CATEGORY')
#  NZBPP_PARSTATUS    - result of par-check:
#                       0 = not checked: par-check is disabled or nzb-file does
#                           not contain any par-files;
#                       1 = checked and failed to repair;
#                       2 = checked and successfully repaired;
#                       3 = checked and can be repaired but repair is disabled.
NZBPP_PARSTATUS = os.getenv('NZBPP_PARSTATUS')
#  NZBPP_UNPACKSTATUS - result of unpack:
#                       0 = unpack is disabled or was skipped due to nzb-file
#                           properties or due to errors during par-check;
#                       1 = unpack failed;
#                       2 = unpack successful.
NZBPP_UNPACKSTATUS = os.getenv('NZBPP_UNPACKSTATUS')
NZBOP_CONFIGFILE = os.getenv('NZBOP_CONFIGFILE')
NZBOP_UNPACK = os.getenv('NZBOP_UNPACK')
NZBPR_PostProcess = os.getenv('NZBPR_PostProcess') 
NZBPR_DestDir = os.getenv('NZBPR_DestDir')
NZBOP_ALLOWREPROCESS = os.getenv('NZBOP_ALLOWREPROCESS')

clientAgent = "nzbget"
try:
    download_id = os.getenv('NZBPR_couchpotato')
except:
    download_id = ""

# Name of script's configuration file
SCRIPT_CONFIG_FILE = "nzbget-postprocess.conf"

# Exit codes
POSTPROCESS_PARCHECK_CURRENT=91
POSTPROCESS_PARCHECK_ALL=92
POSTPROCESS_SUCCESS=93
POSTPROCESS_ERROR=94
POSTPROCESS_NONE=95

# Check if the script is called from nzbget 10.0 or later
if NZBPP_DIRECTORY == "" or NZBOP_CONFIGFILE == "":
    Logger.info("*** NZBGet post-processing script ***") 
    Logger.warning("This script is supposed to be called from nzbget (10.0 or later).") 
    exit(POSTPROCESS_ERROR)

if NZBOP_UNPACK == "":
    Logger.error("This script requires nzbget version at least 10.0-testing-r555 or 10.0-stable.")
    exit(POSTPROCESS_ERROR)

# Check if postprocessing was disabled in postprocessing parameters 
# (for current nzb-file) via web-interface or via command line with 
# "nzbget -E G O PostProcess=no <ID>"
if NZBPR_PostProcess == "no":
    Logger.warning("Post-Process: Post-processing disabled for this nzb-file, exiting") 
    exit(POSTPROCESS_NONE)

Logger.info("Post-Process: Post-processing script successfully started")
#os.chdir(NZBPP_DIRECTORY)

# Determine the location of configuration file (it must be stored in
# the directory with nzbget.conf).
ConfigDir = os.path.dirname(NZBOP_CONFIGFILE)
ScriptConfigFile = os.path.join(ConfigDir, SCRIPT_CONFIG_FILE)
if not os.path.isfile(ScriptConfigFile):
    Logger.error("Post-Process: Configuration file %s not found, exiting", ScriptConfigFile)
    exit(POSTPROCESS_ERROR)

# Readg configuration file
config = ConfigObj(ScriptConfigFile)

Failed_Directory = config['Failed_Directory']
RenameIMG = config['RenameIMG']
JoinTS = config['JoinTS']
SickBeard = config['SickBeard']
SickBeardCategory = config['SickBeardCategory']
CouchPotato = config['CouchPotato']
CouchPotatoCategory = config['CouchPotatoCategory']
HeadPhones = config['HeadPhones']
HeadPhonesCategory = config['HeadPhonesCategory']
Mylar = config['Mylar']
MylarCategory = config['MylarCategory']
Gamez = config['Gamez']
GamezCategory = config['GamezCategory']
FileCleanUp = (config['FileCleanUp']).split(' ')
Delete_Failed = config['Delete_Failed']
Debug = config['Debug']
PostProcess = config['PostProcess']
DestDir = config['DestDir']
Email_successful = (config['Email_successful']).split(' ')
Email_failed = (config['Email_failed']).split(' ')
sendEmail = config['sendEmail']
Email_From = config['Email_From']
Email_To = config['Email_To']
Email_Server = config['Email_Server']
Tsl = config['Tsl']
Email_User = config['Email_User']
Email_Pass = config['Email_Pass']
Email_Subject = config['Email_Subject']
Email_Message = config['Email_Message']
Add_Log = config['Add_Log']

# Check nzbget.conf options
BadConfig = 0

if NZBOP_ALLOWREPROCESS == "yes":
    Logger.error("Post-Process: Please disable option \"AllowReProcess\" in nzbget configuration file")
    BadConfig = 1 

if NZBOP_UNPACK != "yes":
    Logger.error("Post-Process: Please enable option \"Unpack\" in nzbget configuration file")
    BadConfig = 1

if BadConfig == 1:
    Logger.error("Post-Process: Exiting due to incompatible nzbget configuration")
    exit(POSTPROCESS_ERROR)

# Check par status
if NZBPP_PARSTATUS == 3:
    Logger.warning("Post-Process: Par-check successful, but Par-repair disabled, exiting")
    do_exit(POSTPROCESS_NONE)

if NZBPP_PARSTATUS == 1:
    Logger.warning("Post-Process: Par-check failed, exiting")
    do_exit(POSTPROCESS_NONE)

# Check unpack status
if NZBPP_UNPACKSTATUS == 1:
    Logger.warning("Post-Process: Unpack failed, exiting")
    do_exit(POSTPROCESS_NONE)

if NZBPP_UNPACKSTATUS == 0 and NZBPP_PARSTATUS != 2:
    # Unpack is disabled or was skipped due to nzb-file properties or due to errors during par-check

    for dirpath, dirnames, filenames in os.walk(NZBPP_DIRECTORY):
        for file in filenames:
            fileExtension = os.path.splitext(file)[1]

            if fileExtension in ['.rar', '.7z', '.7z']:
                Logger.warning("Post-Process: Archive files exist but unpack skipped, exiting")
                exit(POSTPROCESS_NONE)

            if fileExtension in ['.par2']:
                Logger.warning("Post-Process: Unpack skipped and par-check skipped (although par2-files exist), exiting")
                exit(POSTPROCESS_NONE)

    if os.path.isfile(os.path.join(NZBPP_DIRECTORY, "_brokenlog.txt")):
        Logger.warning("Post-Process: _brokenlog.txt exists, download is probably damaged, exiting")

        exit(POSTPROCESS_NONE)

    Logger.info("Post-Process: Neither archive- nor par2-files found, _brokenlog.txt doesn't exist, considering download successful")

# Check if destination directory exists (important for reprocessing of history items)
if not os.path.isdir(NZBPP_DIRECTORY):
    Logger.error("Post-Process: Nothing to post-process: destination directory $NZBPP_DIRECTORY doesn't exist")
    do_exit(POSTPROCESS_ERROR)

# All checks done, now processing the files

# If download contains only nzb-files move them into nzb-directory
# for further download

AllFilesCount = 0
NZBFilesCount = 0
for dirpath, dirnames, filenames in os.walk(NZBPP_DIRECTORY):
    for file in filenames:
        fileExtension = os.path.splitext(file)[1]
        AllFilesCount = AllFilesCount + 1
        if fileExtension in ['.nzb']:
            NZBFilesCount = NZBFilesCount + 1
if AllFilesCount == NZBFilesCount:
    Logger.info("Moving downloaded nzb-files into incoming nzb-directory for further download")
    for dirpath, dirnames, filenames in os.walk(NZBPP_DIRECTORY):
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            shutil.move(filepath, os.path.join(NZBOP_NZBDIR, file))

# Clean up
Logger.info("Post-Process: Cleaning up")
#call(['chmod', '-R', 'a+w', NZBPP_DIRECTORY])

# Clean up list, space seperated array from GUI
for dirpath, dirnames, filenames in os.walk(NZBPP_DIRECTORY):
    for file in filenames:
        filePath = os.path.join(dirpath, file)
        fileExtension = os.path.splitext(file)[1]
        if fileExtension in FileCleanUp or fileExtension in ['.par']:
            os.unlink(filePath)

if JoinTS == "yes":
    # Join any split .ts files if they are named xxxx.0000.ts xxxx.0001.ts
    # They will be joined together to a file called xxxx.ts
    outputname = ""
    for filename in iglob(os.path.join(NZBPP_DIRECTORY, '*.ts')):
        file, ext = os.path.splitext(filename) # split off the .ts
        file2, ext2 = os.path.splitext(file) # split off the .0001
        outputname = file2 + ext
        break
    if outputname != "":
        Logger.info("Post-Process: Joining ts-files")
        destination = open('outputname', 'wb')
        for filename in iglob(os.path.join(NZBPP_DIRECTORY, '*.ts')):
            shutil.copyfileobj(open(filename, 'rb'), destination)
        destination.close()
        Logger.info("Post-Process: Deleting source ts-files")
        for filename in iglob(os.path.join(NZBPP_DIRECTORY, '*.ts')):
            if filename != outputname:
                os.unlink(filename)

if RenameIMG == "yes":
    # Rename img file to iso
    # It will be renamed to .img.iso so you can see that it has been renamed
    for dirpath, dirnames, filenames in os.walk(NZBPP_DIRECTORY):
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            fileExtension = os.path.splitext(file)[1]
            if fileExtension in ['.img']:
                Logger.info("Post-Process: Renaming img-files to iso")
                newPath = os.path.join(dirpath, file + ".iso")
                shutil.move(filePath, newPath)

# Check if destination directory was set in postprocessing parameters
# (for current nzb-file) via web-interface or via command line with 
# "nzbget -E G O DestDir=/new/path <ID>"
if not (NZBPR_DestDir == None or NZBPR_DestDir == ""):
    Logger.info("Post-Process: moving files to %s", NZBPR_DestDir)
    os.mkdir(NZBPR_DestDir)
    for dirpath, dirnames, filenames in os.walk(NZBPP_DIRECTORY):
        for file in filenames:
            filePath = os.path.join(dirpath, file)
            newPath = os.path,join(NZBPR_DestDir, file)
            shutil.move(filePath, newPath)
    os.chdir(NZBPR_DestDir)
    shutil.rmtree(NZBPP_DIRECTORY)
    NZBPP_DIRECTORY = NZBPR_DestDir
    os.chdir(NZBPP_DIRECTORY)

# All OK, requesting cleaning up of download queue
do_exit(POSTPROCESS_SUCCESS)
