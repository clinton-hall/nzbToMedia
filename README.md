nzbgetToCouchPotato
===================

Provides NZBGet postprocessing for CouchPotatoServer, based on sabToCouchPotato from clinton-hall

To get this to work with NZBGet you have to do the following:

1) Put all the files eg. in a directory wherever you want to keep them (eg. /scripts/ in the home directory of nzbget) and change the permission accordingly so nzbget has access to this files.

2) Add the following lines into nzbget's postprocess.conf in the "PATH" section:

	# Set the full path to sabToCouchpotato.py for Couchpotato's postprocessing
	SabToCouchpotato=<your_path>/sabToCouchpotato.py

3) Add the following lines into nzbget's postprocess.sh right before the line "# Check if destination directory was set in postprocessing parameters"

	if [ $NZBPP_CATEGORY = "movies" -a -e "$SabToCouchpotato" ]; then
        # Call Couchpotatos postprocessing script
        echo "[INFO] Post-Process: Running Couchpotato's postprocessing script ($SabToCouchpotato $NZBPP_DIRECTORY $NZBPP_NZBFILENAME)"
        $PythonCmd $SabToCouchpotato "$NZBPP_DIRECTORY" "$NZBPP_NZBFILENAME" >/dev/null 2>&1
	fi

4)Rename the file autoProcessMovie.cfg.sample to autoProcessMovie.cfg and fill in the appropriate fields as they apply to your installation.

[Notes_On_Delay]
  delay must be a minimum of 60 seconds for the renamer.scan to run successfully. CouchPotato 
  performs a test to ensure files/folder are not newer than 1 minute to prevent renaming of 
  files that are still extracting.

[Notes_On_Method_renamer]
  method "renamer" is the default which will cause CouchPotato to move and rename downloaded files
  as specified in the CouchPotato renamer settings.
  This will also add the movie to the manage list and initiate any configured notifications.
  In this case SABnzbd (or your download client) must extract the files to the "from" folder 
  as specified in your CouchPotato renamer settings. Renamer must be enabled but you should 
  increase the "run every" option in CouchPotato renamer settings (advanced settings) to only 
  run daily (1440) or weekly (10080) or automatic scan can be disabled by setting run every =0.

[Notes_On_Method_manage]
  method "manage" will make CouchPotato update the list of managed movies if manager 
  is enabled but renamer is not enabled.
  In this case SABnzbd (or your download client) must extract the files directly 
  to your final movies folder (as configured in CouchPotato manage settings) and Manage must 
  be enabled.
 
If you have added .py to your PATHEXT (in windows) or you have given sabToCouchPotato.py executable 
permissions, or you are using the compiled executables you can manually call this process outside of 
your nzbclient for testing your configuration or in case a postprocessing event failed.
To do this, execute sabToCouchPotato.py 
e.g. via ssl issue the following command: #./sabToCouchPotato.py
when in the directory where sabToCouchPotato.py is located.