#!/bin/sh 
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


# NZBGet passes following arguments to postprocess-programm as environment
# variables:
#  NZBPP_DIRECTORY    - path to destination dir for downloaded files;
#  NZBPP_NZBNAME      - user-friendly name of processed nzb-file as it is displayed
#                       by the program. The file path and extension are removed.
#                       If download was renamed, this parameter reflects the new name;
#  NZBPP_NZBFILENAME  - name of processed nzb-file. It includes file extension and also
#                       may include full path;
#  NZBPP_CATEGORY     - category assigned to nzb-file (can be empty string);
#  NZBPP_PARSTATUS    - result of par-check:
#                       0 = not checked: par-check is disabled or nzb-file does
#                           not contain any par-files;
#                       1 = checked and failed to repair;
#                       2 = checked and successfully repaired;
#                       3 = checked and can be repaired but repair is disabled.
#  NZBPP_UNPACKSTATUS - result of unpack:
#                       0 = unpack is disabled or was skipped due to nzb-file
#                           properties or due to errors during par-check;
#                       1 = unpack failed;
#                       2 = unpack successful.


# Name of script's configuration file
SCRIPT_CONFIG_FILE="nzbget-postprocess.conf"

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

replaceVarBy() {
	if [ "$Debug" = "yes" ]; then echo "[DETAIL] Post-Process: Executing function 'replaceVarBy'. Going to replace '${2}' in '${1}' by '${3}'" ; fi

	# If we're not using Bash use sed, as we need to support as much as systems possible, also those running sh/dash etc
	if [ -n "${BASH_VERSION}" ]; then
		REPLACEDRESULT="${1/${2}/${3}}"
	else
		REPLACEDRESULT=$(echo "${1}" | sed "s^${2}^${3}^g")
	fi

	if [ "$Debug" = "yes" ]; then echo "[DETAIL] Post-Process: replace result: ${REPLACEDRESULT}" ; fi
}

# Pass on postprocess exit codes to external scripts for handling failed downloads
do_exit() {
	if [ "$Debug" = "yes" ]; then echo "[DETAIL] Post-Process: Executing function 'do_exit' with argument $1" ; fi
	nzbStatus=0
	if [ "$1" -ne "$POSTPROCESS_SUCCESS" ]; then nzbStatus=1 ; fi
	script=none
	nzbToMedia $nzbStatus
        echo "[DETAIL] after calling nzbToMedia"
	replaceVarBy "${Email_Subject}" "<name>" "${NZBPP_NZBFILENAME}"
	replaceVarBy "${REPLACEDRESULT}" "<cat>" "${NZBPP_CATEGORY}"
	replaceVarBy "${REPLACEDRESULT}" "<script>" "${script}"
	Email_Subject="${REPLACEDRESULT}"
	replaceVarBy "${Email_Message}" "<name>" "${NZBPP_NZBFILENAME}"
	replaceVarBy "${REPLACEDRESULT}" "<cat>" "${NZBPP_CATEGORY}"
	replaceVarBy "${REPLACEDRESULT}" "<script>" "${script}"
	Email_Message="${REPLACEDRESULT}"
	for item in $Email_successful; do
	if [ "${NZBPP_CATEGORY}" = "$item" -a "$nzbStatus" = 0 ]; then
		User=""
		if [ -n "$Email_User" -a -n "$Email_Pass" ]; then User="-xu $Email_User -xp $Email_Pass" ; fi
		replaceVarBy "${Email_Subject}" "<status>" "completed"
		Email_Subject="${REPLACEDRESULT}"
		replaceVarBy "${Email_Message}" "<status>" "completed"
		Email_Message="${REPLACEDRESULT}"
		$sendEmail -f "$Email_From" -t "$Email_To" -s "$Email_Server" $User -u "$Email_Subject" -m "$Email_Message" 
	fi; done
	for item in $Email_failed; do
	if [ "${NZBPP_CATEGORY}" = "$item" -a "$nzbStatus" != 0 ]; then
		User=""
		if [ -n "$Email_User" -a -n "$Email_Pass" ]; then User="-xu $Email_User -xp $Email_Pass" ; fi
		replaceVarBy "${Email_Subject}" "<status>" "failed"
		Email_Subject="${REPLACEDRESULT}"
		replaceVarBy "${Email_Message}" "<status>" "failed"
		Email_Message="${REPLACEDRESULT}"
		$sendEmail -f "$Email_From" -t "$Email_To" -s "$Email_Server" $User -u "$Email_Subject" -m "$Email_Message" 
	fi; done
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
	echo "[WARNING] Post-Process: Post-processing disabled for this nzb-file, exiting"
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

if [ "$BadConfig" -eq 1 ]; then
	echo "[ERROR] Post-Process: Exiting due to incompatible nzbget configuration"
	exit $POSTPROCESS_ERROR
fi 

# Check par status
if [ "$NZBPP_PARSTATUS" -eq 1 -o "$NZBPP_PARSTATUS" -eq 3 ]; then
	if [ "$NZBPP_PARSTATUS" -eq 3 ]; then
		echo "[WARNING] Post-Process: Par-check successful, but Par-repair disabled, exiting"
	else
		echo "[WARNING] Post-Process: Par-check failed, exiting"
	fi
	do_exit $POSTPROCESS_NONE
fi 

# Check unpack status
if [ "$NZBPP_UNPACKSTATUS" -ne 2 ]; then
	echo "[WARNING] Post-Process: Unpack failed or disabled, exiting"
	do_exit $POSTPROCESS_NONE
fi 

# Check if destination directory exists (important for reprocessing of history items)
if [ ! -d "$NZBPP_DIRECTORY" ]; then
	echo "[ERROR] Post-Process: Nothing to post-process: destination directory $NZBPP_DIRECTORY doesn't exist"
	do_exit $POSTPROCESS_ERROR
fi

cd "$NZBPP_DIRECTORY"

# All checks done, now processing the files

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
for word in $FileCleanUp ; do rm $word >/dev/null 2>&1 ; done
# Removed by default
rm _brokenlog.txt >/dev/null 2>&1
rm *.[pP][aA][rR]2 >/dev/null 2>&1

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

# Check if destination directory was set in postprocessing parameters
# (for current nzb-file) via web-interface or via command line with 
# "nzbget -E G O DestDir=/new/path <ID>"
if [ "$NZBPR_DestDir" != "" ]; then
	mkdir $NZBPR_DestDir
	mv * $NZBPR_DestDir >/dev/null 2>&1
	cd ..
	rmdir $NZBPP_DIRECTORY
	NZBPP_DIRECTORY=$NZBPR_DestDir
	cd $NZBPP_DIRECTORY
fi

# All OK, requesting cleaning up of download queue
do_exit $POSTPROCESS_SUCCESS
