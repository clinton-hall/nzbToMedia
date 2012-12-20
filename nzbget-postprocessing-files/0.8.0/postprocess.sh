#!/bin/sh 
# -*- coding: cp1252 -*-
#
# Example postprocessing script for NZBGet
#
# Copyright (C) 2008 Peter Roubos <peterroubos@hotmail.com>
# Copyright (C) 2008 Otmar Werner
# Copyright (C) 2008-2012 Andrei Prygunkov <hugbug@users.sourceforge.net>
# Copyright (C) 2012 Antoine Bertin <diaoulael@gmail.com>
# Copyright (C) 2012 J�rgen Seif <thor78@gmx.at>
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
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#

#######################    Usage instructions     #######################
# o  Script will unrar downloaded rar files, join ts-files and rename img-files
#    to iso.
#
# o  To use this script with nzbget set the option "PostProcess" in
#    nzbget configuration file to point to this script file. E.g.:
#        PostProcess=/home/user/nzbget/nzbget-postprocess.sh
#
# o  The script needs a configuration file. An example configuration file
#    is provided in file "postprocess-example.conf". Put the configuration file 
#    into the directory where nzbget's configuration file (nzbget.conf) or where
#    this script itself is located. Then edit the configuration file in any
#    text editor to adjust the settings.
#
# o  You can also edit the script's configuration via web-interface (requires
#    NZBGetWeb 1.4 or later). Set the options "PostProcessConfigFile" and 
#    "PostProcessConfigTemplate" to point to "postprocess-example.conf"
#    (including full path). The both options are under the section 
#    "CONFIGURATION OF POSTPROCESSING-SCRIPT" in NZBGetWeb.
#
# o  There are few options, which can be ajdusted for each nzb-file 
#    individually. To view/edit them in web-interface click on a spanner icon
#    near the name of nzb-file.
#
# o  The script supports the feature called "delayed par-check".
#    That means it can try to unpack downloaded files without par-checking
#    them fisrt. Only if unpack fails, the script schedules par-check,
#    then unpacks again.
#    To use delayed par-check set following options in nzbget configuration file:
#        ParCheck=no
#        ParRepair=yes
#        LoadPars=one (or) LoadPars=all
#
# o  If you want to par-check/repair all files before trying to unpack them,
#    set option "ParCheck=yes".
#
####################### End of Usage instructions #######################


# NZBGet passes following arguments to postprocess-programm as environment
# variables:
#  NZBPP_DIRECTORY    - path to destination dir for downloaded files;
#  NZBPP_NZBFILENAME  - name of processed nzb-file;
#  NZBPP_PARFILENAME  - name of par-file or empty string (if no collections were 
#                       found);
#  NZBPP_PARSTATUS    - result of par-check:
#                       0 = not checked: par-check disabled or nzb-file does
#                           not contain any par-files;
#                       1 = checked and failed to repair;
#                       2 = checked and successfully repaired;
#                       3 = checked and can be repaired but repair is disabled;
#  NZBPP_NZBCOMPLETED - state of nzb-job:
#                       0 = there are more collections in this nzb-file queued;
#                       1 = this was the last collection in nzb-file;
#  NZBPP_PARFAILED    - indication of failed par-jobs for current nzb-file:
#                       0 = no failed par-jobs;
#                       1 = current par-job or any of the previous par-jobs for
#                           the same nzb-files failed;
#  NZBPP_CATEGORY     - category assigned to nzb-file (can be empty string).


# Name of script's configuration file
SCRIPT_CONFIG_FILE="postprocess.conf"

# Exit codes
POSTPROCESS_PARCHECK_CURRENT=91
POSTPROCESS_PARCHECK_ALL=92
POSTPROCESS_SUCCESS=93
POSTPROCESS_ERROR=94
POSTPROCESS_NONE=95

# Postprocessing function for nzbToCouchPotato and nzbToSickBeard
nzbToMedia() {
	if [ "$Debug" = "yes" ]; then echo "[DETAIL] Post-Process: Executing external postprocessing with argument $1" ; fi
	PostProcessStatus=0	
	if [ -n "$1" ]; then PostProcessStatus=$1 ; fi
	if [ "$Debug" = "yes" ]; then echo "[DETAIL] Post-Process: comparing '$NZBPP_CATEGORY' to '$CouchPotatoCategory' and '$SickBeardCategory'" ; fi
	if [ "$NZBPP_CATEGORY" = "$CouchPotatoCategory" ]; then
		if [ "$CouchPotato" = "yes" -a -e "$NzbToCouchPotato" ]; then
			script=$NzbToCouchPotato
			# Call Couchpotato's postprocessing script
			echo "[INFO] Post-Process: Running CouchPotato's postprocessing script"
			if [ "$Debug" = "yes" ]; then
				echo "[DETAIL] Post-Process: CouchPotato-Script-Path=$NzbToCouchPotato" 
				echo "[DETAIL] Post-Process: CouchPotato-Script-ARGV1=$NZBPP_DIRECTORY" 
				echo "[DETAIL] Post-Process: CouchPotato-Script-ARGV2=$NZBPP_NZBFILENAME"
				echo "[DETAIL] Post-Process: CouchPotato-Script-ARGV3=$PostProcessStatus"
			fi
			$PythonCmd $NzbToCouchPotato "$NZBPP_DIRECTORY" "$NZBPP_NZBFILENAME" "$PostProcessStatus" | while read line ; do if [ "$line" != "" ] ; then echo "[INFO] Post-Process: $line" ; fi ; done
		else
			if [ "$CouchPotato" != "yes" ]; then echo "[DETAIL] Post-Process: Ignored to run CouchPotato's postprocessing script as it is disabled by user ('$CouchPotato')"; fi
			if [ ! -e "$NzbToCouchPotato" ]; then echo "[DETAIL] Post-Process: Ignored to run CouchPotato's postprocessing script as the specified script ('$NzbToCouchPotato') does not exist"; fi
		fi
	fi
	if [ "$NZBPP_CATEGORY" = "$SickBeardCategory" ]; then
		if [ "$SickBeard" = "yes" -a -e "$NzbToSickBeard" ]; then
			script=$NzbToSickBeard
			# Call SickBeard's postprocessing script
			echo "[INFO] Post-Process: Running SickBeard's postprocessing script"
			if [ "$Debug" = "yes" ]; then
				echo "[DETAIL] Post-Process: SickBeard-Script-Path=$NzbToSickBeard" 
				echo "[DETAIL] Post-Process: SickBeard-Script-ARGV1=$NZBPP_DIRECTORY" 
				echo "[DETAIL] Post-Process: SickBeard-Script-ARGV2=$NZBPP_NZBFILENAME"
				echo "[DETAIL] Post-Process: SickBeard-Script-ARGV3=$PostProcessStatus"
			fi
			$PythonCmd $NzbToSickBeard "$NZBPP_DIRECTORY" "$NZBPP_NZBFILENAME" "$PostProcessStatus" | while read line ; do if [ "$line" != "" ] ; then echo "[INFO] Post-Process: $line" ; fi ; done
		else
			if [ "$SickBeard" != "yes" ]; then echo "[DETAIL] Post-Process: Ignored to run SickBeard's postprocessing script as it is disabled by user ('$SickBeard')"; fi
			if [ ! -e "$NzbToSickBeard" ]; then echo "[DETAIL] Post-Process: Ignored to run SickBeard's postprocessing script as the specified script ('$NzbToSickBeard') does not exist"; fi
		fi
	fi
	if [ "$NZBPP_CATEGORY" = "$CustomCategory" ]; then
		if [ "$Custom" = "yes" -a -e "$CustomScript" ]; then
			script=$CustomScript
			# Call Custom postprocessing script
			echo "[INFO] Post-Process: Running the Custom postprocessing script"
			if [ "$Debug" = "yes" ]; then
				echo "[DETAIL] Post-Process: Custom-Script-Path=$CustomScript" 
				echo "[DETAIL] Post-Process: Custom-Script-ARGV1=$NZBPP_DIRECTORY" 
				echo "[DETAIL] Post-Process: Custom-Script-ARGV2=$NZBPP_NZBFILENAME"
				echo "[DETAIL] Post-Process: Custom-Script-ARGV3=$PostProcessStatus"
			fi
			$CustomCmd $CustomScript "$NZBPP_DIRECTORY" "$NZBPP_NZBFILENAME" "$PostProcessStatus" | while read line ; do if [ "$line" != "" ] ; then echo "[INFO] Post-Process: $line" ; fi ; done
		else
			if [ "$Custom" != "yes" ]; then echo "[DETAIL] Post-Process: Ignored to run the Custom postprocessing script as it is disabled by user ('$Custom')"; fi
			if [ ! -e "$CustomScript" ]; then echo "[DETAIL] Post-Process: Ignored to run the Custom postprocessing script as the specified script ('$CustomScript') does not exist"; fi
		fi
	fi
}

# Pass on postprocess exit codes to external scripts for handling failed downloads
do_exit() {
	if [ "$Debug" = "yes" ]; then echo "[DETAIL] Post-Process: Executing function 'do_exit' with argument $1" ; fi
	nzbStatus=0
	if [ "$1" -ne "$POSTPROCESS_SUCCESS" ]; then nzbStatus=1 ; fi
	script=none
	nzbToMedia $nzbStatus
	Email_Subject="${Email_Subject/<name>/$NZBPP_NZBFILENAME}"
	Email_Subject="${Email_Subject/<cat>/$NZBPP_CATEGORY}"
	Email_Subject="${Email_Subject/<script>/$script}"
	Email_Message="${Email_Message/<name>/$NZBPP_NZBFILENAME}"
	Email_Message="${Email_Message/<cat>/$NZBPP_CATEGORY}"
	Email_Message="${Email_Message/<script>/$script}"
	if [ "$Email_successful" = "yes" -a "$nzbStatus" = 0 ]; then
		User=""
		if [ -n "$Email_User" -a -n "$Email_Pass" ]; then User="-xu $Email_User -xp $Email_Pass" ; fi
		Email_Subject="${Email_Subject/<status>/completed}"
		Email_Message="${Email_Message/<status>/completed}"
		$sendEmail -f "$Email_From" -t "$Email_To" -s "$Email_Server" $User -u "$Email_Subject" -m "$Email_Message" 
	fi
	if [ "$Email_failed" = "yes" -a "$nzbStatus" != 0 ]; then
		User=""
		if [ -n "$Email_User" -a -n "$Email_Pass" ]; then User="-xu $Email_User -xp $Email_Pass" ; fi
		Email_Subject="${Email_Subject/<status>/failed}"
		Email_Message="${Email_Message/<status>/failed}"
		$sendEmail -f "$Email_From" -t "$Email_To" -s "$Email_Server" $User -u "$Email_Subject" -m "$Email_Message" 
	fi
	exit $1
}

# Check if the script is called from nzbget
if [ "$NZBPP_DIRECTORY" = "" -o "$NZBOP_CONFIGFILE" = "" ]; then
	echo "*** NZBGet post-process script ***"
	echo "This script is supposed to be called from nzbget (0.7.0 or later)."
	exit $POSTPROCESS_ERROR
fi 

# Check if postprocessing was disabled in postprocessing parameters 
# (for current nzb-file) via web-interface or via command line with 
# "nzbget -E G O PostProcess=no <ID>"
if [ "$NZBPR_PostProcess" = "no" ]; then
	echo "[WARNING] Post-Process: Postprocessing disabled for this nzb-file, exiting"
	exit $POSTPROCESS_NONE
fi

echo "[INFO] Post-Process: Post-process script successfully started"

# Determine the location of configuration file (it must be stored in
# the directory with nzbget.conf or in this script's directory).
ConfigDir="${NZBOP_CONFIGFILE%/*}"
ScriptConfigFile="$ConfigDir/$SCRIPT_CONFIG_FILE"
if [ ! -f "$ScriptConfigFile" ]; then
	ConfigDir="${0%/*}"
	ScriptConfigFile="$ConfigDir/$SCRIPT_CONFIG_FILE"
fi
if [ ! -f "$ScriptConfigFile" ]; then
	echo "[ERROR] Post-Process: Configuration file $ScriptConfigFile not found, exiting"
	exit $POSTPROCESS_ERROR
fi

# Readg configuration file
while read line; do	eval "$line"; done < $ScriptConfigFile

# Check nzbget.conf options
BadConfig=0

if [ "$NZBOP_ALLOWREPROCESS" = "yes" ]; then
	echo "[ERROR] Post-Process: Please disable option \"AllowReProcess\" in nzbget configuration file"
	BadConfig=1
fi 

if [ "$NZBOP_LOADPARS" = "none" ]; then
	echo "[ERROR] Post-Process: Please set option \"LoadPars\" to \"One\" or \"All\" in nzbget configuration file"
	BadConfig=1
fi

if [ "$NZBOP_PARREPAIR" = "no" ]; then
	echo "[ERROR] Post-Process: Please set option \"ParRepair\" to \"Yes\" in nzbget configuration file"
	BadConfig=1
fi

if [ "$BadConfig" -eq 1 ]; then
	echo "[ERROR] Post-Process: Exiting because of not compatible nzbget configuration"
	exit $POSTPROCESS_ERROR
fi 

# Check if all collections in nzb-file were downloaded
if [ ! "$NZBPP_NZBCOMPLETED" -eq 1 ]; then
	echo "[INFO] Post-Process: Not the last collection in nzb-file, exiting"
	exit $POSTPROCESS_SUCCESS
fi 

# Check par status
if [ "$NZBPP_PARSTATUS" -eq 1 -o "$NZBPP_PARSTATUS" -eq 3 -o "$NZBPP_PARFAILED" -eq 1 ]; then
	if [ "$NZBPP_PARSTATUS" -eq 3 ]; then
		echo "[WARNING] Post-Process: Par-check successful, but Par-repair disabled, exiting"
	else
		echo "[WARNING] Post-Process: Par-check failed, exiting"
	fi
	do_exit $POSTPROCESS_ERROR
fi 

# Check if destination directory exists (important for reprocessing of history items)
if [ ! -d "$NZBPP_DIRECTORY" ]; then
	echo "[ERROR] Post-Process: Nothing to post-process: destination directory $NZBPP_DIRECTORY doesn't exist"
	do_exit $POSTPROCESS_ERROR
fi

cd "$NZBPP_DIRECTORY"

# If not just repaired and file "_brokenlog.txt" exists, the collection is damaged
# exiting with returning code $POSTPROCESS_PARCHECK_ALL to request par-repair
if [ ! "$NZBPP_PARSTATUS" -eq 2 ]; then
	if [ -f "_brokenlog.txt" ]; then
		if (ls *.[pP][aA][rR]2 >/dev/null 2>&1); then
			echo "[INFO] Post-Process: Brokenlog found, requesting par-repair"
			do_exit $POSTPROCESS_PARCHECK_ALL
		fi
	fi
fi

# All checks done, now processing the files

# Flag indicates that something was unrared
Unrared=0
   
# Unrar the files (if any) to the temporary directory, if there are no rar files this will do nothing
if (ls *.rar >/dev/null 2>&1); then

	# Check if unrar exists
	$UnrarCmd >/dev/null 2>&1
	if [ "$?" -eq 127 ]; then
		echo "[ERROR] Post-Process: Unrar not found. Set the path to unrar in script's configuration"
		do_exit $POSTPROCESS_ERROR
	fi

	# Make a temporary directory to store the unrarred files
	ExtractedDirExists=0
	if [ -d $ExtractedDir ]; then
		ExtractedDirExists=1
	else
		mkdir $ExtractedDir
	fi
	
	echo "[INFO] Post-Process: Unraring"
	rarpasswordparam=""
	if [ "$NZBPR_Password" != "" ]; then
		rarpasswordparam="-p$NZBPR_Password"
	fi

	$UnrarCmd x -y -p- "$rarpasswordparam" -o+ "*.rar"  ./$ExtractedDir/
	if [ "$?" -eq 3 ]; then
		echo "[ERROR] Post-Process: Unrar failed"
		if [ "$ExtractedDirExists" -eq 0 ]; then
			rm -R $ExtractedDir
		fi
		# for delayed par-check/-repair at least one par-file must be already downloaded
		if (ls *.[pP][aA][rR]2 >/dev/null 2>&1); then
			echo "[INFO] Post-Process: Requesting par-repair"
			do_exit $POSTPROCESS_PARCHECK_ALL
		fi
		do_exit $POSTPROCESS_ERROR
	fi
	Unrared=1
   
	# Remove the rar files
	if [ "$DeleteRarFiles" = "yes" ]; then
		echo "[INFO] Post-Process: Deleting rar-files"
		rm *.r[0-9][0-9] >/dev/null 2>&1
		rm *.rar >/dev/null 2>&1
		rm *.s[0-9][0-9] >/dev/null 2>&1
	fi
	
	# Go to the temp directory and try to unrar again.  
	# If there are any rars inside the extracted rars then these will no also be unrarred
	cd $ExtractedDir
	if (ls *.rar >/dev/null 2>&1); then
		echo "[INFO] Post-Process: Unraring (second pass)"
		$UnrarCmd x -y -p- -o+ "*.rar"

		if [ "$?" -eq 3 ]; then
			echo "[INFO] Post-Process: Unrar (second pass) failed"
			do_exit $POSTPROCESS_ERROR
		fi

		# Delete the Rar files
		if [ "$DeleteRarFiles" = "yes" ]; then
			echo "[INFO] Post-Process: Deleting rar-files (second pass)"
			rm *.r[0-9][0-9] >/dev/null 2>&1
			rm *.rar >/dev/null 2>&1
			rm *.s[0-9][0-9] >/dev/null 2>&1
		fi
	fi
	
	# Move everything back to the Download folder
	mv * ..
	cd ..
	rmdir $ExtractedDir
fi

# If download contains only nzb-files move them into nzb-directory
# for further download
# Check if command "wc" exists
wc -l . >/dev/null 2>&1
if [ "$?" -ne 127 ]; then
	AllFilesCount=`ls -1 2>/dev/null | wc -l`
	NZBFilesCount=`ls -1 *.nzb 2>/dev/null | wc -l`
	if [ "$AllFilesCount" -eq "$NZBFilesCount" ]; then
		echo "[INFO] Moving downloaded nzb-files into incoming nzb-directory for further download"
		mv *.nzb $NZBOP_NZBDIR
	fi
fi

# Clean up
echo "[INFO] Post-Process: Cleaning up"
chmod -R a+rw .
# Clean up list, space seperated array from GUI
for item in ${FileCleanUp[*]} ; do rm $item >/dev/null 2>&1 ; done
# Removed by default
rm _brokenlog.txt >/dev/null 2>&1
if [ "$Unrared" -eq 1 ]; then
	# Delete par2-file only if there were files for unpacking.
	rm *.[pP][aA][rR]2 >/dev/null 2>&1
fi

if [ "$JoinTS" = "yes" ]; then
	# Join any split .ts files if they are named xxxx.0000.ts xxxx.0001.ts
	# They will be joined together to a file called xxxx.0001.ts
	if (ls *.ts >/dev/null 2>&1); then
	    echo "[INFO] Post-Process: Joining ts-files"
		tsname=`find . -name "*0001.ts" |awk -F/ '{print $NF}'`
		cat *0???.ts > ./$tsname
	fi   
   
	# Remove all the split .ts files
    echo "[INFO] Post-Process: Deleting source ts-files"
	rm *0???.ts >/dev/null 2>&1
fi

if [ "$RenameIMG" = "yes" ]; then
	# Rename img file to iso
	# It will be renamed to .img.iso so you can see that it has been renamed
	if (ls *.img >/dev/null 2>&1); then
	    echo "[INFO] Post-Process: Renaming img-files to iso"
		imgname=`find . -name "*.img" |awk -F/ '{print $NF}'`
		mv $imgname $imgname.iso
	fi   
fi

############################
### BEGIN CUSTOMIZATIONS ###
############################

# Move categories to /share/your_directory and remove download destination directory
# Test for category and ensure the passed directory exists as a directory.
if [ "$NZBPP_CATEGORY" = "$SickBeardCategory" -a -d "$TvDownloadDir" ]; then
        echo "[INFO] Post-Process: Moving TV shows to $TvDownloadDir"
        cp -R "$NZBPP_DIRECTORY" "$TvDownloadDir"
        if [ "$?" -ne 0 ]; then
           echo "[ERROR] Post-Process: Moving to $TvDownloadDir"
           exit $POSTPROCESS_ERROR
        else
           rm -fr *
           cd ..
           rmdir "$NZBPP_DIRECTORY"
           NZBPP_DIRECTORY="$TvDownloadDir"
	   cd "$NZBPP_DIRECTORY"
        fi
fi
# Test for category and ensure the passed directory exists as a directory.
if [ "$NZBPP_CATEGORY" = "$CouchPotatoCategory" -a -d "$MoviesDownloadDir" ]; then
        echo "[INFO] Post-Process: Moving Movies to $MoviesDownloadDir" 
        cp -R "$NZBPP_DIRECTORY" "$MoviesDownloadDir" 
        if [ "$?" -ne 0 ]; then
           echo "[ERROR] Post-Process: Moving to $MoviesDownloadDir"
           exit $POSTPROCESS_ERROR
        else
           rm -fr *
           cd ..
           rmdir "$NZBPP_DIRECTORY"
           NZBPP_DIRECTORY="$MoviesDownloadDir"
	   cd "$NZBPP_DIRECTORY"
        fi
fi
# Test for category and ensure the passed directory exists as a directory.
if [ "$NZBPP_CATEGORY" = "$CustomCategory" -a -d "$CustomDownloadDir" ]; then
        echo "[INFO] Post-Process: Moving $CustomCategory to $CustomDownloadDir" 
        cp -R "$NZBPP_DIRECTORY" "$CustomDownloadDir" 
        if [ "$?" -ne 0 ]; then
           echo "[ERROR] Post-Process: Moving to $CustomDownloadDir"
           exit $POSTPROCESS_ERROR
        else
           rm -fr *
           cd ..
           rmdir "$NZBPP_DIRECTORY"
           NZBPP_DIRECTORY="$CustomDownloadDir"
	   cd "$NZBPP_DIRECTORY"
        fi
fi
                                                                                                                                                                                                                                               
##########################
### END CUSTOMIZATIONS ###
##########################

# Check if destination directory was set in postprocessing parameters
# (for current nzb-file) via web-interface or via command line with 
# "nzbget -E G O DestDir=/new/path <ID>"
if [ "$NZBPR_DestDir" != "" ]; then
	mkdir $NZBPR_DestDir
	mv * $NZBPR_DestDir >/dev/null 2>&1
	cd ..
	rmdir $NZBPP_DIRECTORY
	NZBPP_DIRECTORY=$NZBPR_DestDir	
	cd "$NZBPP_DIRECTORY"
fi

# All OK, requesting cleaning up of download queue
do_exit $POSTPROCESS_SUCCESS
