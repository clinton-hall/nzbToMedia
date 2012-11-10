sabToCouchPotato
================

Provides SABnzbd postprocessing for CouchPotatoServer

Rename the file autoProcessMovie.cfg.sample to autoProcessMovie.cfg and fill in the appropriate fields as 
they apply to your installation.

In order to utilize failed download handling in CPS you will need to chnage the following settings in sabnzbd:
sabnzbd, config, switches, Post-Process Only Verified Jobs = Off
sabnzbd, config, special, empty_postproc = On


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
sabnzbd for testing your configuration or in case a postprocessing event failed.
To do this, execute sabToCouchPotato.py 
e.g. via ssl issue the following command: #./sabToCouchPotato.py
when in the directory where sabToCouchPotato.py is located.