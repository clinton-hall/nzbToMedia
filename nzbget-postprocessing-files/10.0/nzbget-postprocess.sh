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
	if [ "$Debug" = "yes" ]; then echo "[DETAIL] Post-Process: Executing external postprocessing with argument $1" | tee -a tmp.log; fi
	PostProcessStatus=0	
	if [ -n "$1" ]; then PostProcessStatus=$1 ; fi
	if [ "$Debug" = "yes" ]; then echo "[DETAIL] Post-Process: comparing '$NZBPP_CATEGORY' to '$CouchPotatoCategory' and '$SickBeardCategory'" | tee -a tmp.log; fi
	find "$NZBPP_DIRECTORY" -type f -size -200000k -iname \*sample\* -exec rm {} \; >/dev/null 2>&1
	if [ "$NZBPP_CATEGORY" = "$CouchPotatoCategory" ]; then
		if [ "$CouchPotato" = "yes" -a -e "$NzbToCouchPotato" ]; then
			script=$NzbToCouchPotato
			# Call Couchpotato's postprocessing script
			echo "[INFO] Post-Process: Running CouchPotato's postprocessing script" | tee -a tmp.log
			if [ "$Debug" = "yes" ]; then
				echo "[DETAIL] Post-Process: CouchPotato-Script-Path=$NzbToCouchPotato" | tee -a tmp.log
				echo "[DETAIL] Post-Process: CouchPotato-Script-ARGV1=$NZBPP_DIRECTORY" | tee -a tmp.log
				echo "[DETAIL] Post-Process: CouchPotato-Script-ARGV2=$NZBPP_NZBFILENAME" | tee -a tmp.log
				echo "[DETAIL] Post-Process: CouchPotato-Script-ARGV3=$PostProcessStatus" | tee -a tmp.log
			fi
			$PythonCmd $NzbToCouchPotato "$NZBPP_DIRECTORY" "$NZBPP_NZBFILENAME" "$PostProcessStatus" "$NZBPP_CATEGORY" | while read line ; do if [ "$line" != "" ] ; then replaceLogLine "${line}" ; fi ; done
		else
			if [ "$CouchPotato" != "yes" ]; then echo "[DETAIL] Post-Process: Ignored to run CouchPotato's postprocessing script as it is disabled by user ('$CouchPotato')" | tee -a tmp.log; fi
			if [ ! -e "$NzbToCouchPotato" ]; then echo "[DETAIL] Post-Process: Ignored to run CouchPotato's postprocessing script as the specified script ('$NzbToCouchPotato') does not exist" | tee -a tmp.log; fi
		fi
	fi
	if [ "$NZBPP_CATEGORY" = "$SickBeardCategory" ]; then
		if [ "$SickBeard" = "yes" -a -e "$NzbToSickBeard" ]; then
			script=$NzbToSickBeard
			# Call SickBeard's postprocessing script
			echo "[INFO] Post-Process: Running SickBeard's postprocessing script" | tee -a tmp.log
			if [ "$Debug" = "yes" ]; then
				echo "[DETAIL] Post-Process: SickBeard-Script-Path=$NzbToSickBeard" | tee -a tmp.log
				echo "[DETAIL] Post-Process: SickBeard-Script-ARGV1=$NZBPP_DIRECTORY" | tee -a tmp.log
				echo "[DETAIL] Post-Process: SickBeard-Script-ARGV2=$NZBPP_NZBFILENAME" | tee -a tmp.log
				echo "[DETAIL] Post-Process: SickBeard-Script-ARGV3=$PostProcessStatus" | tee -a tmp.log
			fi
			$PythonCmd $NzbToSickBeard "$NZBPP_DIRECTORY" "$NZBPP_NZBFILENAME" "$PostProcessStatus" "$NZBPP_CATEGORY" | while read line ; do if [ "$line" != "" ] ; then replaceLogLine "${line}" ; fi ; done
		else
			if [ "$SickBeard" != "yes" ]; then echo "[DETAIL] Post-Process: Ignored to run SickBeard's postprocessing script as it is disabled by user ('$SickBeard')" | tee -a tmp.log; fi
			if [ ! -e "$NzbToSickBeard" ]; then echo "[DETAIL] Post-Process: Ignored to run SickBeard's postprocessing script as the specified script ('$NzbToSickBeard') does not exist" | tee -a tmp.log; fi
		fi
	fi
	if [ "$NZBPP_CATEGORY" = "$HeadPhonesCategory" ]; then
		if [ "$HeadPhones" = "yes" -a -e "$NzbToHeadPhones" ]; then
			script=$NzbToHeadPhones
			# Call HeadPhones' postprocessing script
			echo "[INFO] Post-Process: Running HeadPhones' postprocessing script" | tee -a tmp.log
			if [ "$Debug" = "yes" ]; then
				echo "[DETAIL] Post-Process: HeadPhones-Script-Path=$NzbToHeadPhones" | tee -a tmp.log
				echo "[DETAIL] Post-Process: HeadPhones-Script-ARGV1=$NZBPP_DIRECTORY" | tee -a tmp.log
				echo "[DETAIL] Post-Process: HeadPhones-Script-ARGV2=$NZBPP_NZBFILENAME" | tee -a tmp.log
				echo "[DETAIL] Post-Process: HeadPhones-Script-ARGV3=$PostProcessStatus" | tee -a tmp.log
			fi
			$PythonCmd $NzbToHeadPhones "$NZBPP_DIRECTORY" "$NZBPP_NZBFILENAME" "$PostProcessStatus" "$NZBPP_CATEGORY" | while read line ; do if [ "$line" != "" ] ; then replaceLogLine "${line}" ; fi ; done
		else
			if [ "$HeadPhones" != "yes" ]; then echo "[DETAIL] Post-Process: Ignored to run HeadPhones' postprocessing script as it is disabled by user ('$HeadPhones')" | tee -a tmp.log; fi
			if [ ! -e "$NzbToHeadPhones" ]; then echo "[DETAIL] Post-Process: Ignored to run HeadPhones' postprocessing script as the specified script ('$NzbToHeadPhones') does not exist" | tee -a tmp.log; fi
		fi
	fi
	if [ "$NZBPP_CATEGORY" = "$MylarCategory" ]; then
		if [ "$Mylar" = "yes" -a -e "$NzbToMylar" ]; then
			script=$NzbToMylar
			# Call Mylar's postprocessing script
			echo "[INFO] Post-Process: Running Mylar's postprocessing script" | tee -a tmp.log
			if [ "$Debug" = "yes" ]; then
				echo "[DETAIL] Post-Process: Mylar-Script-Path=$NzbToMylar" | tee -a tmp.log
				echo "[DETAIL] Post-Process: Mylar-Script-ARGV1=$NZBPP_DIRECTORY" | tee -a tmp.log
				echo "[DETAIL] Post-Process: Mylar-Script-ARGV2=$NZBPP_NZBFILENAME" | tee -a tmp.log
				echo "[DETAIL] Post-Process: Mylar-Script-ARGV3=$PostProcessStatus" | tee -a tmp.log
			fi
			$PythonCmd $NzbToMylar "$NZBPP_DIRECTORY" "$NZBPP_NZBFILENAME" "$PostProcessStatus" "$NZBPP_CATEGORY" | while read line ; do if [ "$line" != "" ] ; then replaceLogLine "${line}" ; fi ; done
		else
			if [ "$Mylar" != "yes" ]; then echo "[DETAIL] Post-Process: Ignored to run Mylar's postprocessing script as it is disabled by user ('$Mylar')" | tee -a tmp.log; fi
			if [ ! -e "$NzbToMylar" ]; then echo "[DETAIL] Post-Process: Ignored to run Mylar's postprocessing script as the specified script ('$NzbToMylar') does not exist" | tee -a tmp.log; fi
		fi
	fi
	if [ "$NZBPP_CATEGORY" = "$GamezCategory" ]; then
		if [ "$Gamez" = "yes" -a -e "$NzbToGamez" ]; then
			script=$NzbToGamez
			# Call Gamez's postprocessing script
			echo "[INFO] Post-Process: Running Gamez's postprocessing script" | tee -a tmp.log
			if [ "$Debug" = "yes" ]; then
				echo "[DETAIL] Post-Process: Gamez-Script-Path=$NzbToGamez" | tee -a tmp.log
				echo "[DETAIL] Post-Process: Gamez-Script-ARGV1=$NZBPP_DIRECTORY" | tee -a tmp.log
				echo "[DETAIL] Post-Process: Gamez-Script-ARGV2=$NZBPP_NZBFILENAME" | tee -a tmp.log
				echo "[DETAIL] Post-Process: Gamez-Script-ARGV3=$PostProcessStatus" | tee -a tmp.log
			fi
			$PythonCmd $NzbToGamez "$NZBPP_DIRECTORY" "$NZBPP_NZBFILENAME" "$PostProcessStatus" "$NZBPP_CATEGORY" | while read line ; do if [ "$line" != "" ] ; then replaceLogLine "${line}" ; fi ; done
		else
			if [ "$Gamez" != "yes" ]; then echo "[DETAIL] Post-Process: Ignored to run Gamez's postprocessing script as it is disabled by user ('$Gamez')" | tee -a tmp.log; fi
			if [ ! -e "$NzbToGamez" ]; then echo "[DETAIL] Post-Process: Ignored to run Gamez's postprocessing script as the specified script ('$NzbToGamez') does not exist" | tee -a tmp.log; fi
		fi
	fi
	if [ "$NZBPP_CATEGORY" = "$CustomCategory" ]; then
		if [ "$Custom" = "yes" -a -e "$CustomScript" ]; then
			script=$CustomScript
			# Call Custom postprocessing script
			echo "[INFO] Post-Process: Running the Custom postprocessing script" | tee -a tmp.log
			if [ "$Debug" = "yes" ]; then
				echo "[DETAIL] Post-Process: Custom-Script-Path=$CustomScript" | tee -a tmp.log
				echo "[DETAIL] Post-Process: Custom-Script-ARGV1=$NZBPP_DIRECTORY" | tee -a tmp.log
				echo "[DETAIL] Post-Process: Custom-Script-ARGV2=$NZBPP_NZBFILENAME" | tee -a tmp.log
				echo "[DETAIL] Post-Process: Custom-Script-ARGV3=$PostProcessStatus" | tee -a tmp.log
			fi
			$CustomCmd $CustomScript "$NZBPP_DIRECTORY" "$NZBPP_NZBFILENAME" "$PostProcessStatus" "$NZBPP_CATEGORY" | while read line ; do if [ "$line" != "" ] ; then replaceLogLine "${line}" ; fi ; done
		else
			if [ "$Custom" != "yes" ]; then echo "[DETAIL] Post-Process: Ignored to run the Custom postprocessing script as it is disabled by user ('$Custom')" | tee -a tmp.log; fi
			if [ ! -e "$CustomScript" ]; then echo "[DETAIL] Post-Process: Ignored to run the Custom postprocessing script as the specified script ('$CustomScript') does not exist" | tee -a tmp.log; fi
		fi
	fi
}

replaceVarBy() {
	if [ "$Debug" = "yes" ]; then echo "[DETAIL] Post-Process: Executing function 'replaceVarBy'. Going to replace '${2}' in '${1}' by '${3}'" | tee -a tmp.log; fi

	# If we're not using Bash use sed, as we need to support as much as systems possible, also those running sh/dash etc
	if [ -n "${BASH_VERSION}" ]; then
		REPLACEDRESULT="${1/${2}/${3}}"
	else
		REPLACEDRESULT=$(echo "${1}" | sed "s^${2}^${3}^g")
	fi

	if [ "$Debug" = "yes" ]; then echo "[DETAIL] Post-Process: replace result: ${REPLACEDRESULT}" | tee -a tmp.log; fi
}

replaceLogLine() {
	# This converts the output logigng from nzbTo* script to a compatible format with NZBGet
	# If we're not using Bash use sed, as we need to support as much as systems possible, also those running sh/dash etc
	if [ -n "${BASH_VERSION}" ]; then
		newline="${1/*DEBUG/[DETAIL]}"
		newline="${newline/*INFO/[INFO]}"
		newline="${newline/*WARNING/[WARNING]}"
		newline="${newline/*ERROR/[ERROR]}"
	else
		newline=$(echo "${1}" | sed "s^.*DEBUG^[DETAIL]^")
		newline=$(echo $newline | sed "s^.*INFO^[INFO]^")
		newline=$(echo $newline | sed "s^.*WARNING^[WARNING]^")
		newline=$(echo $newline | sed "s^.*ERROR^[ERROR]^")
	fi
	echo "$newline" | tee -a tmp.log
}

# Pass on postprocess exit codes to external scripts for handling failed downloads
do_exit() {
	if [ "$Debug" = "yes" ]; then echo "[DETAIL] Post-Process: Executing function 'do_exit' with argument $1" | tee -a tmp.log; fi
	nzbStatus=0
	if [ "$1" -ne "$POSTPROCESS_SUCCESS" ]; then 
		if [ "$Delete_Failed" = "yes" ]; then
			rm * >/dev/null 2>&1
			cd ..
			rmdir $NZBPP_DIRECTORY
		else
			mkdir $Failed_Directory
			mv * $Failed_Directory >/dev/null 2>&1
			cd ..
			rmdir $NZBPP_DIRECTORY
    			NZBPP_DIRECTORY=$Failed_Directory
    			cd $NZBPP_DIRECTORY
		fi
		nzbStatus=1 
	fi
	script=none
	nzbToMedia $nzbStatus
        echo "[DETAIL] after calling nzbToMedia" | tee -a tmp.log
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
		if [ "${Add_Log}" = "yes" ]; then 
			Email_Message="$Email_Message \r\nLog Result"
			while read line; do Email_Message="$Email_Message \r\n$line"; done < tmp.log
		fi
		$sendEmail -f "$Email_From" -t "$Email_To" -s "$Email_Server" -o "tsl=$Tsl" $User -u "$Email_Subject" -m "$Email_Message" 
	fi; done
	for item in $Email_failed; do
	if [ "${NZBPP_CATEGORY}" = "$item" -a "$nzbStatus" != 0 ]; then
		User=""
		if [ -n "$Email_User" -a -n "$Email_Pass" ]; then User="-xu $Email_User -xp $Email_Pass" ; fi
		replaceVarBy "${Email_Subject}" "<status>" "failed"
		Email_Subject="${REPLACEDRESULT}"
		replaceVarBy "${Email_Message}" "<status>" "failed"
		Email_Message="${REPLACEDRESULT}"
		if [ "${Add_Log}" = "yes" ]; then 
			Email_Message="$Email_Message \r\nLog Result"
			while read line; do Email_Message="$Email_Message \r\n$line"; done < tmp.log
		fi
		$sendEmail -f "$Email_From" -t "$Email_To" -s "$Email_Server" -o "tsl=$Tsl" $User -u "$Email_Subject" -m "$Email_Message" 
	fi; done
	exit $1
}

# Check if the script is called from nzbget 10.0 or later
if [ "$NZBPP_DIRECTORY" = "" -o "$NZBOP_CONFIGFILE" = "" ]; then
    echo "*** NZBGet post-processing script ***" 
    echo "This script is supposed to be called from nzbget (10.0 or later)." 
    exit $POSTPROCESS_ERROR
fi
if [ "$NZBOP_UNPACK" = "" ]; then
    echo "[ERROR] This script requires nzbget version at least 10.0-testing-r555 or 10.0-stable." 
    exit $POSTPROCESS_ERROR
fi 

# Check if postprocessing was disabled in postprocessing parameters 
# (for current nzb-file) via web-interface or via command line with 
# "nzbget -E G O PostProcess=no <ID>"
if [ "$NZBPR_PostProcess" = "no" ]; then
	echo "[WARNING] Post-Process: Post-processing disabled for this nzb-file, exiting" 
	exit $POSTPROCESS_NONE
fi

echo "[INFO] Post-Process: Post-processing script successfully started" | tee tmp.log
cd "$NZBPP_DIRECTORY" 

# Determine the location of configuration file (it must be stored in
# the directory with nzbget.conf).
ConfigDir="${NZBOP_CONFIGFILE%/*}"
ScriptConfigFile="$ConfigDir/$SCRIPT_CONFIG_FILE"
if [ ! -f "$ScriptConfigFile" ]; then
	echo "[ERROR] Post-Process: Configuration file $ScriptConfigFile not found, exiting" | tee -a tmp.log
	exit $POSTPROCESS_ERROR
fi

# Readg configuration file
while read line; do	eval "$line"; done < $ScriptConfigFile

# Check nzbget.conf options
BadConfig=0

if [ "$NZBOP_ALLOWREPROCESS" = "yes" ]; then
	echo "[ERROR] Post-Process: Please disable option \"AllowReProcess\" in nzbget configuration file" | tee -a tmp.log
	BadConfig=1
fi 

if [ "$NZBOP_UNPACK" != "yes" ]; then
    echo "[ERROR] Post-Process: Please enable option \"Unpack\" in nzbget configuration file" | tee -a tmp.log
	BadConfig=1
fi

if [ "$BadConfig" -eq 1 ]; then
	echo "[ERROR] Post-Process: Exiting due to incompatible nzbget configuration" | tee -a tmp.log
	exit $POSTPROCESS_ERROR
fi 

# Check par status
if [ "$NZBPP_PARSTATUS" -eq 3 ]; then
	echo "[WARNING] Post-Process: Par-check successful, but Par-repair disabled, exiting" | tee -a tmp.log
	do_exit $POSTPROCESS_NONE
fi
if [ "$NZBPP_PARSTATUS" -eq 1 ]; then
    echo "[WARNING] Post-Process: Par-check failed, exiting" | tee -a tmp.log
    do_exit $POSTPROCESS_NONE
fi 

# Check unpack status
if [ "$NZBPP_UNPACKSTATUS" -eq 1 ]; then
	echo "[WARNING] Post-Process: Unpack failed, exiting" | tee -a tmp.log
	do_exit $POSTPROCESS_NONE
fi 
if [ "$NZBPP_UNPACKSTATUS" -eq 0 -a "$NZBPP_PARSTATUS" -ne 2 ]; then
    # Unpack is disabled or was skipped due to nzb-file properties or due to errors during par-check

	if (ls *.rar *.7z *.7z.??? >/dev/null 2>&1); then
		echo "[WARNING] Post-Process: Archive files exist but unpack skipped, exiting" | tee -a tmp.log
		exit $POSTPROCESS_NONE
	fi

	if (ls *.par2 >/dev/null 2>&1); then
		echo "[WARNING] Post-Process: Unpack skipped and par-check skipped (although par2-files exist), exiting" | tee -a tmp.log
		exit $POSTPROCESS_NONE
	fi

	if [ -f "_brokenlog.txt" ]; then
		echo "[WARNING] Post-Process: _brokenlog.txt exists, download is probably damaged, exiting" | tee -a tmp.log
		exit $POSTPROCESS_NONE
	fi

	echo "[INFO] Post-Process: Neither archive- nor par2-files found, _brokenlog.txt doesn't exist, considering download successful" | tee -a tmp.log
fi

# Check if destination directory exists (important for reprocessing of history items)
if [ ! -d "$NZBPP_DIRECTORY" ]; then
    echo "[ERROR] Post-Process: Nothing to post-process: destination directory $NZBPP_DIRECTORY doesn't exist" | tee -a tmp.log
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
		echo "[INFO] Moving downloaded nzb-files into incoming nzb-directory for further download" | tee -a tmp.log
		mv *.nzb $NZBOP_NZBDIR
	fi
fi

# Clean up
echo "[INFO] Post-Process: Cleaning up" | tee -a tmp.log
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
        echo "[INFO] Post-Process: Joining ts-files" | tee -a tmp.log
		tsname=`find . -name "*0001.ts" |awk -F/ '{print $NF}'`
		cat *0???.ts > ./$tsname

        # Remove all the split .ts files
        echo "[INFO] Post-Process: Deleting source ts-files" | tee -a tmp.log
        rm *0???.ts >/dev/null 2>&1
    fi
fi

if [ "$RenameIMG" = "yes" ]; then
	# Rename img file to iso
	# It will be renamed to .img.iso so you can see that it has been renamed
	if (ls *.img >/dev/null 2>&1); then
	    echo "[INFO] Post-Process: Renaming img-files to iso" | tee -a tmp.log
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
