nzbToCouchPotato
================

Provides an efficient way to handle postprocessing for [CouchPotatoServer](https://couchpota.to/ "CouchPotatoServer") 
when using one of the popular NZB download clients like [SABnzbd](http://sabnzbd.org/) and [NZBGet](http://nzbget.sourceforge.net/ "NZBGet") on low performance systems like a NAS. 
This script is based on [sabToCouchPotato] (https://github.com/clinton-hall/sabToCouchPotato "sabToCouchPotato") from Clinton Hall, but extends the original script with the support for NZBGet.

Introduction
------------
My Synology DS211j was too weak to provide decent downloads rates with SABnzbd and CouchPotatoServer even by using sabToCouchPotato.
The only alternative was to switch to NZBGet which uses far less resources and helped to reach the full download speed. 
But i was still unsatisfied as i could not use sabToCouchPotato anymore. 
Even worse the renamer of CouchPotatoServer caused broken downloads by interfering with NZBGet while it was still unpacking the files. 
In needed a solution and out of this motivation i started working on a own version of sabToCouchPotato named "nzbToCouchPotato".

Installation
------------
### General
1. Put all files in a directory wherever you want to keep them (eg. /scripts/ in the home directory of your nzb client) 
   and change the permission accordingly so the nzb client can access to this files. 

2. Rename the file autoProcessMovie.cfg.sample to autoProcessMovie.cfg and fill in the appropriate 
   fields as they apply to your installation.

	[Notes_On_Delay]
	Delay must be a minimum of 60 seconds for the renamer.scan to run successfully. CouchPotato 
	performs a test to ensure files/folder are not newer than 1 minute to prevent renaming of 
	files that are still extracting. 

	[Notes_On_Method_renamer]
	Method "renamer" is the default which will cause CouchPotato to move and rename downloaded files
	as specified in the CouchPotato renamer settings.
	This will also add the movie to the manage list and initiate any configured notifications.
	In this case your nzb client must extract the files to the "from" folder 
	as specified in your CouchPotato renamer settings. Renamer must be enabled 
	but automatic scan can be disabled by setting "Run Every" to "0".

	[Notes_On_Method_manage]
	Method "manage" will make CouchPotato update the list of managed movies if manager 
	is enabled but renamer is not enabled.
	In this case your nzb client must extract the files directly 
	to your final movies folder (as configured in CouchPotato manage settings) and Manage must 
	be enabled.

3. If you have added .py to your PATHEXT (in windows) or you have given nzbToCouchPotato.py executable 
   permissions, or you are using the compiled executables you can manually call this process outside of 
   your nzb client for testing your configuration or in case a postprocessing event failed.
   To do this, execute nzbToCouchPotato.py e.g. via ssl issue the following command: 
   $ ./nzbToCouchPotato.py when in the directory where nzbToCouchPotato.py is located.

### SABnzbd
If you are using SABnzbd perform the following steps to configure postprocessing for "nzbToCouchPotato":

1. In SABnzbd go to "Config" -> "Folders", then configure in the section "User Folders"
   the option "Post-Processing Scripts Folder" with the path where you keep the post-processings scripts for SABnzbd.
   
2. Then go to "Config" -> "Categories" 
   and configure the category which you want to use for CouchPotato (eg. movies) 
   then select "nzbToCouchPotato.py" as the script that shall be executed after the job was finished by SABnzbd.
   
3. For better handling of failed downloads in version 0.7.5 of SABnzbd a new special parameter named "empty_postproc" was introduced,
   so at last go to "Config" -> "Special" in the web-interface and tick the option "empty_postproc".
   
   Description of this special parameter according to SABnzbd manual: 
   > Do post-processing and run the user script even if nothing has been downloaded. 
   This is useful in combination with tools like SickBeard, for which running the script on an empty or failed download is a trigger to try an alternative NZB. 
   Note that the "Status" parameter for the script will be -1. [0.7.5+ only]
   
### NZBGet
If you are using NZBGet perform the following steps to configure postprocessing for "nzbToCouchPotato":

1. Replace the config files with the ones from the download below according to the version you are using (0.8.0 or 9.0):
   https://github.com/downloads/thorli/nzbToCouchPotato/nzbget-postprocessing-files.zip 

   These files enable additional postprocessing settings for CouchPotato (and SickBeard as well) in the NZBGet webinterface. 
   If NZBGet is running either restart (0.8.0) or reload (9.0) to activate the changes after you have replaced the files. 
   To be on the safe side, don't forget to make a backup of the existing files!

2. In NZBGet go to "POSTPROCESSING SCRIPT" -> "PATHS" and apply the option "NzbToCouchpotato" according to your environment, 
   this setting configures the path where NZBGet has to look for "nzbToCouchpotato.py".

3. Then go to "POSTPROCESSING SCRIPT" -> "OPTIONS" and set there the category which you want to use for CouchPotato post-processing.