nzbToMedia
================

Provides an efficient way to handle postprocessing for [CouchPotatoServer](https://couchpota.to/ "CouchPotatoServer") and [SickBeard](http://sickbeard.com/ "SickBeard")
when using one of the popular NZB download clients like [SABnzbd](http://sabnzbd.org/) and [NZBGet](http://nzbget.sourceforge.net/ "NZBGet") on low performance systems like a NAS. 
This script is based on sabToSickBeard (written by Nic Wolfe and supplied with SickBeard), with the support for NZBGet being added by [thorli](https://github.com/thorli "thorli") and further contributions by [schumi2004](https://github.com/schumi2004 "schumi2004") and [hugbug](https://sourceforge.net/apps/phpbb/nzbget/memberlist.php?mode=viewprofile&u=67 "hugbug")

Introduction
------------
Originally this was modifed from the SickBeard version to allow for "on-demand" renaming and not have My QNAP TS-412 NAS constantly scanning the download directory. 
Later, a few failed downloads prompted me to incorporate "failed download" handling.
Failed download handling is now provided for sabnzbd, by CouchPotatoServer; however on arm processors (e.g. small NAS systems) this can be un-reliable.

thorli's Synology DS211j was too weak to provide decent download rates with SABnzbd and CouchPotatoServer even by using sabToCouchPotato; His only alternative (as with many many QNAP and Synology users) was to switch to NZBGet which uses far less resources and helps to reach the full download speed. 

The renamer of CouchPotatoServer caused broken downloads by interfering with NZBGet while it was still unpacking the files. Hence the solution was thorli's version of sabToCouchPotato which has now been named "nzbToCouchPotato".

Failed download handling for SickBeard is available by using the development branch from fork [SickBeard-failed](https://github.com/Tolstyak/Sick-Beard.git "SickBeard-failed")
To use this feature, in autoProcessTV.cfg set the parameter "failed_fork=1". Default is 0 and will work with standard version of SickBeard and just ignores failed downloads.

Installation
------------
### General

1. Put all files in a directory wherever you want to keep them (eg. /scripts/ in the home directory of your nzb client) 
   and change the permission accordingly so the nzb client can access to this files. 

### nzbToSickBeard

1. Rename the file autoProcessTV.cfg.sample to autoProcessTV.cfg and fill in the appropriate 
   fields as they apply to your installation.

	host: Set this to "localhost" if SickBeard and your download client are on the same system. otherwise enter the ipaddress of the system SickBeard is insatlled on.
	
	port: Set this to the port that SickBeard is running on.
	
	username: Set this to the user name required to log on to the SickBeard web GUI. (optional)
	
	password: Set this to the password required to log on to the SickBeard web GUI. (optional)
	
	web_root: Set this to the web_root value specified in SickBeard for Apache Reverse Proxy. (optional)
	
	ssl: Set this to "1" if you access SickBeard via ssl (https) otherwise leave this as "0" for http.
	
	watch_dir: Set this only if SickBeard is on another PC to your download client and the directory structure is different.(optional)
	
	failed_fork: Set this to "1" if you are using the failed fork branch. Otherwise set this to "0". (optional)

### nzbToCouchPotato

1. Rename the file autoProcessMovie.cfg.sample to autoProcessMovie.cfg and fill in the appropriate 
   fields as they apply to your installation.

	host: Set this to "localhost" if CouchPotatoServer and your download client are on the same system. otherwise enter the ipaddress of the system SickBeard is insatlled on.
	
	port: Set this to the port that CouchPotatoServer is running on.
	
	username: Set this to the user name required to log on to the CouchPotatoServer web GUI. (optional)
	
	password: Set this to the password required to log on to the CouchPotatoServer web GUI. (optional)
	
	web_root: Set this to the web_root value specified in CouchPotatoServer for Apache Reverse Proxy. (optional)
	
	ssl: Set this to "1" if you access CouchPotatoServer via ssl (https) otherwise leave this as "0" for http.
	
	Delay: Delay must be a minimum of 60 seconds for the renamer.scan to run successfully. CouchPotatoServer performs a test to ensure files/folder are not newer than 1 minute to prevent renaming of files that are still extracting. 
	
	apikey: Enter the api key used for CouchPotatoServer. Found in CouchPotatoServer->settings->general (addvanced setting)
	
	Method:	Method "renamer" is the default which will cause CouchPotatoserver to move and rename downloaded files as specified in the CouchPotatoServer renamer settings.
	This will also add the movie to the manage list and initiate any configured notifications.
	In this case your nzb client must extract the files to the "from" folder as specified in your CouchPotatoServer renamer settings. Renamer must be enabled but automatic scan can be disabled by setting "Run Every" to "0".
	
	Method "manage" will make CouchPotatoServer update the list of managed movies if manager is enabled but renamer is not enabled.
	In this case your nzb client must extract the files directly to your final movies folder (as configured in CouchPotatoServer manage settings) and Manage must be enabled.

3. If you have added .py to your PATHEXT (in windows) or you have given nzbToCouchPotato.py executable permissions, or you are using the compiled executables you can manually call this process outside of your nzb client for testing your configuration or in case a postprocessing event failed.  
	To do this, execute nzbToCouchPotato.py e.g. via ssl issue the following command: 
   	$ ./nzbToCouchPotato.py when in the directory where nzbToCouchPotato.py is located.

### SickBeard

The following must be configured in SickBeard:

1. Config -> Search Settings -> NZB Search

	i.   NZB Method = Either SABnzbd or NZBget as appropriate
	
	ii.  NZBget HOST:PORT - SABnzbd URL = the url/host and port for your download client.

	iii. SABnzbd Username = The username required to log in to sabnzbd web GUI
	
	iv.  NZBget Password - SABnzbd Passowrd =  The password required to log in to your download client's web GUI.
	
	v.   SABnzbd API Key = The api key used by SABnzbd (Found in sabnzbd -> config -> general -> SABnzbd Web Server)
	
	vi.  NZBGet Category - SABnzbd Category = A category that is used by your download client (e.g. "TV", or "SickBeard")

2. Settings -> Post Processing -> Post Processing
	
	i.   TV Download Dir = blank
	
	ii.  Keep Original Files = user choice. (option)
	
	iii. Move Associated Files = user choice. (option)

	iv.  Rename Episodes = must be ticked.
	
	v.   Scan and Process = must be unticked.

3. Settings -> Post Processing -> Naming
	
	The naming must be specified as per user choice. 
	
	This naming will be applied to all shows processed via the postprocess script. 

4. Settings -> Post Processing -> Metadata
	
	The metadata wanted must be specified as per user choice. 
	
	This metadata creationg will be applied to all shows processed via the postprocess script.

### CouchPotatoServer

The following must be configured in CouchPotatoServer:

1. Settings -> Downloaders -> Sabnzbd (or NZBGet)

	i.   Host = The url/host and port for your download client.
	
	ii.  Api Key = The api key used by SABnzbd (Sabnzbd only: Found in sabnzbd -> config -> general -> SABnzbd Web Server)
	
	iii. Password = The password required to log in to NZBget's web GUI. (NZBget only)
	
	iv.  Category = A category that is used by your downlaod client (e.g. "movies", or "CouchPotato")
	
	v.   Delete Failed = Should be unticked (Sabnzbd only)

2. Settings -> Renamer -> "Rename downloaded movies" should be checked and the settings below applied:

	i.   From = Must be set to the full path to your completed download movies (including any additional category paths)

		e.g. %sabnzbd_download_complete/movies
	
	ii.  To = Must be set to the folder where you want your movie library to be kept. this would also usually be added to manage.
	
	iii. Run Every = Should be set to a high interval (e.g. 1440 = 24 hours) or disabled by setting "0"
	
	iv.  Force Every = Should be set to a high interval (e.g 24 hours) or disabled by setting "0"
	
	v.   Next On_failed = Should be unticked.

	> These last 3 settings are "advanced settings" so to change these you will need to select the option "show advanced settings" on the top right of all settings pages.

### SABnzbd

If you are using SABnzbd perform the following steps to configure postprocessing for "nzbToCouchPotato":

1. In SABnzbd go to "Config" -> "Folders", then configure in the section "User Folders"
   the option "Post-Processing Scripts Folder" with the path where you keep the post-processings scripts for SABnzbd.
   
2. Go to "Config" -> "Categories" 
   and configure the category which you want to use for CouchPotato (eg. "movies" as set in the CPS Downloaders settings) 
   then select "nzbToCouchPotato.py" as the script that shall be executed after the job was finished by SABnzbd.
   "Folder/Path" should be set to the location where you want your mvies extracted to (the Renamer "From" directory as set up in CPS) 

3. Go to "Config" -> "Switches" and un-tick the option "Post-Process Only Verified Jobs" 
   in order to allow for snatching of the next best release from CouchPotatoServer when a downlaod fails.
   
4. For better handling of failed downloads in version 0.7.5 of SABnzbd a new special parameter named "empty_postproc" was introduced,
   so at last go to "Config" -> "Special" in the web-interface and tick the option "empty_postproc".
   
   Description of this special parameter according to SABnzbd manual: 
   > Do post-processing and run the user script even if nothing has been downloaded. 
   This is useful in combination with tools like SickBeard, for which running the script on an empty or failed download is a trigger to try an alternative NZB. 
   Note that the "Status" parameter for the script will be -1. [0.7.5+ only]
   
### NZBGet

If you are using NZBGet perform the following steps to configure postprocessing for "nzbToCouchPotato":

1. Replace the config files with the ones from the included "nzbget-postprocessing-files" according to the version you are using (0.8.0 or 9.0):

   These files enable additional postprocessing settings for CouchPotato and SickBeard, as well as a "Custom" postprocess script, in the NZBGet webinterface. 
   If NZBGet is running either restart (0.8.0) or reload (9.0) to activate the changes after you have replaced the files. 
   To be on the safe side, don't forget to make a backup of the existing files!

2. In NZBGet go to "POSTPROCESSING SCRIPT" -> "PATHS" and change as needed:
 
	i.   Set the full path to python if it is not in your PATH.
	
		PythonCmd=/usr/local/python/bin/python

	ii.  Set the full path to sabToSickBeard.py for SickBeard's postprocessing.
		
		NzbToSickBeard=/usr/local/nzbget/var/nzbToSickBeard.py

	iii. Set the full path where completed movies should be placed before SickBeard's Renamer is called (option)
		
		TvDownloadDir=

	iv.  Set the full path to nzbToCouchpotato.py for Couchpotato's postprocessing

		NzbToCouchPotato=/usr/local/nzbget/var/nzbToCouchPotato.py

	v.   Set the full path where completed movies should be placed before CouchPotato's Renamer is called (option)
		
		MoviesDownloadDir=

	vi.  Set the full path to any dependency required for your Custom Postprocess script if it is not in your PATH.
	
		CustomCmd=/usr/local/python/bin/python

	vii. Set the full path to the Custom Postprocess script. (option)
	
		CustomScript=

	viii.Set the full path where completed downloads should be placed before the Custom postprocess is called (option)
		
		CustomDownloadDir=
	
3. Then go to "POSTPROCESSING SCRIPT" -> "OPTIONS" and set: 

	i.   Perform SickBeard's postprocessing (yes, no).

		SickBeard=yes

	ii.  Category for SickBeard's postprocessing.
		
		SickBeardCategory=tv

	iii. Perform Couchpotato's postprocessing (yes, no).

		CouchPotato=yes

	iv.  Category for Couchpotato's postprocessing. (option)
		
		CouchPotatoCategory=movies

	v.   Perform Custom postprocessing (yes, no). (option)
		
		Custom=
  	
	vi.  Category for Custom postprocessing (eg. movies) (option)
		
		CustomCategory=

4. Then go to "POSTPROCESSING SCRIPT" -> "EMAIL-PARAMETERS" and set:

	i.   Specify if you want emails to be sent for successful downloads.
		
		Email_successful=yes

	ii.  Specify if you want emails to be sent for failed downloads.
		
		Email_failed=yes

	iii. Set the full path and file name for sendEmail application (as supplied in this repository).
		
		sendEmail=/usr/local/nzbget/var/sendEmail/sendEmail

	iv.  Enter the email address you want this email to be sent from. 
		
		Email_From=nzbget@nas.home

	v.   Enter the email address you want this email to be sent to. 
		
		Email_To=me@home.net

	vi.  Enter smtp server and port. eg smtp.live.com:25 
		
		Email_Server=smtp.live.com:25

	vii. Enter your smtp server user name (if required)
		
		Email_User=

	viii.Enter your smtp server password (if required)

		Email_Pass=

	ix.  Enter your email subject in quotes.

		Use <status> to add 'completed'/'failed'
	
		Use <name> to add the nzb name
	
		Use <cat> to add the download categoty.
	
		Use <script> to name the external script used.
		
		Email_Subject="The Download of <name> has <status>"

	x.   Enter your email message in quotes.
	
		Use the same substitutes as described above.
	
		Use /n for new line.
		
		Email_Message="The download of <name> has <status> /n This has been processed by the script <script> for category <cat>" 
