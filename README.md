nzbToMedia
================

Provides an efficient way to handle postprocessing for [CouchPotatoServer](https://couchpota.to/ "CouchPotatoServer") and [SickBeard](http://sickbeard.com/ "SickBeard")
when using one of the popular NZB download clients like [SABnzbd](http://sabnzbd.org/) and [NZBGet](http://nzbget.sourceforge.net/ "NZBGet") on low performance systems like a NAS. 
This script is based on sabToSickBeard (written by Nic Wolfe and supplied with SickBeard), with the support for NZBGet being added by [thorli](https://github.com/thorli "thorli") and further contributions by [schumi2004](https://github.com/schumi2004 "schumi2004") and [hugbug](https://sourceforge.net/apps/phpbb/nzbget/memberlist.php?mode=viewprofile&u=67 "hugbug").
Torrent suport added by [jkaberg](https://github.com/jkaberg "jkaberg") and [berkona](https://github.com/berkona "berkona")

Introduction
------------
Originally this was modifed from the SickBeard version to allow for "on-demand" renaming and not have My QNAP TS-412 NAS constantly scanning the download directory. 
Later, a few failed downloads prompted me to incorporate "failed download" handling.
Failed download handling is now provided for sabnzbd, by CouchPotatoServer; however on arm processors (e.g. small NAS systems) this can be un-reliable.

thorli's Synology DS211j was too weak to provide decent download rates with SABnzbd and CouchPotatoServer even by using sabToCouchPotato; His only alternative (as with many many QNAP and Synology users) was to switch to NZBGet which uses far less resources and helps to reach the full download speed. 

The renamer of CouchPotatoServer caused broken downloads by interfering with NZBGet while it was still unpacking the files. Hence the solution was thorli's version of sabToCouchPotato which has now been named "nzbToCouchPotato".

Failed download handling for SickBeard is available by using the development branch from fork [SickBeard-failed](https://github.com/Tolstyak/Sick-Beard.git "SickBeard-failed")
To use this feature, in autoProcessTV.cfg set the parameter "failed_fork=1". Default is 0 and will work with standard version of SickBeard and just ignores failed downloads.

Torrent support has been added with the assistance of jkaberg and berkona. Currently supports uTorrent, Transmissions, Deluge and possibly more.

Installation
------------

### Windows

Download the the compiled versions of this code here [nzbToMedia - win.zip](https://dl.dropbox.com/u/68130597/nzbToMedia%20-%20win.zip "nzbToMedia - win.zip")

For nzbget downlaod the Full package with nzbget support (including shell script environment) from here [nzbToMedia - win - nzbget support.zip](https://dl.dropbox.com/u/68130597/nzbToMedia%20-%20win%20-%20nzbget%20support.zip "nzbToMedia - win - nzbget support.zip")

Copy all files from *\nzbToMedia\nzbget-postprocessing-files\Shell\ to a location in your system path, 
or add the location of these files to the system path.
e.g. copy to "C:\Program Files (x86)\Shell\" and add "C:\Program Files (x86)\Sheel" to system path.

### General

1. Put all files in a directory wherever you want to keep them (eg. /scripts/ in the home directory of your nzb client) 
   and change the permission accordingly so the nzb client can access these files. 

### nzbToSickBeard

1. Rename the file autoProcessMedia.cfg.sample to autoProcessMedia.cfg and fill in the appropriate 
   fields in [SickBeard] as they apply to your installation.

	category: This is only required for TorrentToMedia.
	
	outputDirectory:  This is only required for TorrentToMedia.
	
	host: Set this to "localhost" if SickBeard and your download client are on the same system. otherwise enter the ipaddress of the system SickBeard is insatlled on.
	
	port: Set this to the port that SickBeard is running on.
	
	username: Set this to the user name required to log on to the SickBeard web GUI. (optional)
	
	password: Set this to the password required to log on to the SickBeard web GUI. (optional)
	
	web_root: Set this to the web_root value specified in SickBeard for Apache Reverse Proxy. (optional)
	
	ssl: Set this to "1" if you access SickBeard via ssl (https) otherwise leave this as "0" for http.
	
	watch_dir: Set this only if SickBeard is on another PC to your download client and the directory structure is different.(optional)
	
	failed_fork: Set this to "1" if you are using the failed fork branch. Otherwise set this to "0". (optional)
	
2. If you have added .py to your PATHEXT (in windows) or you have given nzbToSickBeard.py executable permissions, or you are using the compiled executables you can manually call this process outside of your nzb client for testing your configuration or in case a postprocessing event failed.  
	To do this, execute nzbToSickBeard.py e.g. double-click in Windows or via ssh/shell issue the following command: 
   	$ ./nzbToSickBeard.py when in the directory where nzbToSickBeard.py is located.
	note: you must have watch_dir set to use nzbToSickBeard for a manual scan.

### nzbToCouchPotato

1. Rename the file autoProcessMedia.cfg.sample to autoProcessMedia.cfg and fill in the appropriate 
   fields in [CouchPotato] as they apply to your installation.

	category: This is only required for TorrentToMedia.
	
	outputDirectory:  This is only required for TorrentToMedia.
	
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
	
	delete_failed: Set this to "1" if you want this script to delete all files and folders related to a download that has failed.
	setting this to "0" will not delete any files.
	note. this is not given as an option for SickBeard since the failed_fork in SickBeard supports this feature.

2. If you have added .py to your PATHEXT (in windows) or you have given nzbToCouchPotato.py executable permissions, or you are using the compiled executables you can manually call this process outside of your nzb client for testing your configuration or in case a postprocessing event failed.  
	To do this, execute nzbToCouchPotato.py e.g. double-click in Windows or via ssh/shell issue the following command: 
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
	
2. Config -> Search Settings -> Search Torrents
	
	i.   Torrent Black Hole = Enter your Torrent downlaoder's BlackHole Directory + tv sub directory

		/usr/local/blackhole/tv
	
3. Settings -> Post Processing -> Post Processing
	
	i.   TV Download Dir = blank
	
	ii.  Keep Original Files = user choice. (option)
	
	iii. Move Associated Files = user choice. (option)

	iv.  Rename Episodes = must be ticked.
	
	v.   Scan and Process = must be unticked.

4. Settings -> Post Processing -> Naming
	
	The naming must be specified as per user choice. 
	
	This naming will be applied to all shows processed via the postprocess script. 

5. Settings -> Post Processing -> Metadata
	
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
	
2. Settings -> Downloaders -> Transmission

	i.   Host = The url/host and port for Transmission.
	
	ii.  username = The user name required to log in to Transmission
	
	iii. password = The password required to log in to Transmission
	
	iv.  Directory = The directory for completed/seeding files. NOT the renamer "from" directory.
		
		/usr/local/Download/movies
	
3. Settings -> Downloaders -> uTorrent

	i.   Host = The url/host and port for uTorrent.
	
	ii.  username = The user name required to log in to uTorrent
	
	iii. password = The password required to log in to uTorrent
	
	iv.  label = label/category to be used by the postprocessing script.
		
		movies
		
4. Settings -> Downloaders -> BlackHole

	i.   Directory = Enter your Torrent downlaoder's BlackHole Directory + movies sub directory

		/usr/local/blackhole/movies
	
	ii.  use for = Torrents, Usenet, or Both. 
		If using SABnzbd of NZBget for Usenet, and balckhole for torrents, select "torrents" only.

5. Settings -> Renamer -> "Rename downloaded movies" should be checked and the settings below applied:

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
 
	i.   Set the full path to python if it is not in your PATH. (option is required)
		These scripts now have -x permissions and should be as such on your system. Python needs to be in your system path.	

		PythonCmd=/usr/local/python/bin/python

	ii.  Set the full path to sabToSickBeard.py for SickBeard's postprocessing.
		
		NzbToSickBeard=/usr/local/nzbget/var/nzbToSickBeard.py

	iii. Set the full path where completed movies should be placed before SickBeard's Renamer is called (option)
		(v 9.0 only). For n 10.0 set this in the appropriate category settings in the Categories Section.
		
		TvDownloadDir=

	iv.  Set the full path to nzbToCouchpotato.py for Couchpotato's postprocessing

		NzbToCouchPotato=/usr/local/nzbget/var/nzbToCouchPotato.py

	v.   Set the full path where completed movies should be placed before CouchPotato's Renamer is called (option)
		(v 9.0 only). For n 10.0 set this in the appropriate category settings in the Categories Section.
		
		MoviesDownloadDir=

	vi.  Set the full path to any dependency required for your Custom Postprocess script if it is not in your PATH.(option is required)
	
		CustomCmd=/usr/local/python/bin/python

	vii. Set the full path to the Custom Postprocess script. (option)
	
		CustomScript=

	viii.Set the full path where completed downloads should be placed before the Custom postprocess is called (option)
		(v 9.0 only). For n 10.0 set this in the appropriate category settings in the Categories Section.
		
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

	ix.  Enter your email subject, in single quotes.

		Use <status> to add 'completed'/'failed'
	
		Use <name> to add the nzb name
	
		Use <cat> to add the download categoty.
	
		Use <script> to name the external script used.
		
		Email_Subject='The download of <name> has <status>.'

	x.   Enter your email message, in single quotes.
	
		Use the same substitutes as described above.
	
		Use \r\n for new line.
		
		Email_Message='The download of <name> has <status>. \r\n This has been processed by the script <script> for category <cat>' 

### µTorrent

If you are using µTorrent, perform the following steps to configure postprocessing for "TorrentToMedia":

1. Rename the autoProcessMedia.cfg.sample to autoProcessMedia.cfg and edit the parameters:

	i.   [Torrent} uselink = 1 to allow hard-linking of files
		quicker and less harddisk used, if download and final location are on the same hard-disk
		set uselink = 0 to use normal copy options. 
		Any movement across hard disks / network MUST use "0"

	ii.  [Torrent] extractiontool (Windows Only...you will need to install [7-zip](http://www.7-zip.org/ "7-zip"))
		
		C:\Program Files\7-Zip\7z.exe' 
		
	iii. [Torrent] categories: all categories/labels/sub-directories used by your downloader.
		
		music,music_videos,pictures,software
	
	iv.  [Torrent] compressedExtentions: all extensions you want to be identified and extracted
		
		.zip,.rar,.7z,.gz,.bz,.tar,.arj
 	
	v.   [Torrent] mediaExtentions: all extensions you want to be identified as videos and processed.
		
		.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso
	
	vi.  [Torrent] metaExtentions: all other extensions you want to be processed. other extensions will be ignored.
		
		.nfo,.sub,.srt,.jpg,.gif

	vii. [CouchPotato] & [SickBeard] category: you must set the category that is passed from these applications
		If using "blackhole-subdirectory", this is the last folder name used in the blackhole.
		
		e.g. tv or movies
		
	viii.[CouchPotato] & [SickBeard] outputDirectory: you must set the absoluet path to extract videos to.
		this destination, for CouchPotato, must match the CouchPotato Renamer's, "from" directory.
		
	ix.  [CouchPotato] & [SickBeard]: 
		Configure the remaining settings as describes in nzbToCouchPotato and nzbToSickBeard above.


2. In µTorrent go to preferences > Advanced > Run Program > Run this program when torrent finishes:
 
	i.   Set full path to script, pass paramaters as "utorrent" "%D" "%N" "%L".
	
		/usr/local/utorrent/nzbToMedia/TorrentToMedia.py "utorrent" "%D" "%N" "%L"
	
3. In uTorrent set the following directories.
 
	i.   Preferences, directories, "Move Completed Downlaods to" = Enabled 
		"Apprend Torrents Label" = Enabled
		Set the directory = The directory where downloaded files stay while seeding.
		This is NOT the "FROM" directory in CouchPotato renamer. 
	
		/usr/local/Download/

	ii.   Preferences, directories, "Automatically load .torrents from"
		= The balckhole directory used by CouchPotato and/or SickBeard
				 
    		/usr/local/blackhole

4. Output from TorrentToMedia will be logged where the scripts reside, in a file called "postprocess.log"

### Transmission

If you are using Transmission, perform the following steps to configure postprocessing for "TorrentToMedia":

1. Rename the autoProcessMedia.cfg.sample to autoProcessMedia.cfg and edit the parameters:

	i.   [Torrent} uselink = 1 to allow hard-linking of files
		quicker and less harddisk used, if download and final location are on the same hard-disk
		set uselink = 0 to use normal copy options. 
		Any movement across hard disks / network MUST use "0"

	ii.  [Torrent] extractiontool (Windows Only...you will need to install [7-zip](http://www.7-zip.org/ "7-zip"))
		
		C:\Program Files\7-Zip\7z.exe'
		
	iii. [Torrent] categories: all categories/labels/sub-directories used by your downloader.
		
		music,music_videos,pictures,software
	
	iv.  [Torrent] compressedExtentions: all extensions you want to be identified and extracted
		
		.zip,.rar,.7z,.gz,.bz,.tar,.arj
 	
	v.   [Torrent] mediaExtentions: all extensions you want to be identified as videos and processed.
		
		.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso
	
	vi.  [Torrent] metaExtentions: all other extensions you want to be processed. other extensions will be ignored.
		
		.nfo,.sub,.srt,.jpg,.gif

	vii. [CouchPotato] & [SickBeard] category: you must set the category that is passed from these applications
		This is the last folder name in the directory path passed as "directory for completed downloads."
		If using "blackhole-subdirectory", this is the last folder name used in the blackhole.
		
		e.g. tv or movies
		
	viii.[CouchPotato] & [SickBeard] outputDirectory: you must set the absoluet path to extract videos to.
		this destination, for CouchPotato, must match the CouchPotato Renamer's, "from" directory.
			
		/usr/local/extracted/movies
		/usr/local/extracted/tv
		
	ix.  [CouchPotato] & [SickBeard]: 
		Configure the remaining settings as describes in nzbToCouchPotato and nzbToSickBeard above.


2. In Transmission add the TorrentToMedia.py script to run on downlaod complete.
 
	i.   On some systems go to Preferences->Transfers->Management
		Select the script to run on download complete.
	
		/usr/local/transmission/nzbToMedia/TorrentToMedia.py

	ii.   On other systems you will need to edit settings.json 
		(usually /etc/transmission-daemon/settings.json). 
		Edit while the daemon is not running.
		
    		"script-torrent-done-enabled": true, 
    		"script-torrent-done-filename": "/usr/local/transmission/nzbToMedia/TorrentToMedia.py",

3. In Transmission set the following directories (settings.json, or interface).
 
	i.   Download Directory = The directory where downloaded files stay while seeding.
		This is NOT the "FROM" directory in CouchPotato renamer. 
	
		"download-dir": "/usr/local/Download",

	ii.   Watch Direcetory = The balckhole directory used by CouchPotato and/or SickBeard
				 
    		"watch-dir": "/usr/local/blackhole',
    		"watch-dir-enabled": true,

4. Output from TorrentToMedia will be logged where the scripts reside, in a file called "postprocess.log"


### Deluge

If you are using Deluge, perform the following steps to configure postprocessing for "TorrentToMedia":

1. Rename the autoProcessMedia.cfg.sample to autoProcessMedia.cfg and edit the parameters:

	i.   [Torrent} uselink = 1 to allow hard-linking of files
		quicker and less harddisk used, if download and final location are on the same hard-disk
		set uselink = 0 to use normal copy options. 
		Any movement across hard disks / network MUST use "0"

	ii.  [Torrent] extractiontool (Windows Only...you will need to install [7-zip](http://www.7-zip.org/ "7-zip"))
		
		C:\Program Files\7-Zip\7z.exe' 
		
	iii. [Torrent] categories: all categories/labels/sub-directories used by your downloader.
		
		music,music_videos,pictures,software
	
	iv.  [Torrent] compressedExtentions: all extensions you want to be identified and extracted
		
		.zip,.rar,.7z,.gz,.bz,.tar,.arj
 	
	v.   [Torrent] mediaExtentions: all extensions you want to be identified as videos and processed.
		
		.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso
	
	vi.  [Torrent] metaExtentions: all other extensions you want to be processed. other extensions will be ignored.
		
		.nfo,.sub,.srt,.jpg,.gif

	vii. [CouchPotato] & [SickBeard] category: you must set the category that is passed from these applications
		If using "blackhole-subdirectory", this is the last folder name used in the blackhole.
		
		e.g. tv or movies
		
	viii.[CouchPotato] & [SickBeard] outputDirectory: you must set the absoluet path to extract videos to.
		this destination, for CouchPotato, must match the CouchPotato Renamer's, "from" directory.
		
	ix.  [CouchPotato] & [SickBeard]: 
		Configure the remaining settings as describes in nzbToCouchPotato and nzbToSickBeard above.


2. In Deluge, enable the plugin in the Plugins menu in Preferences. 
	For the webUI; reopen the Preferences menu for the Execute plugin to be available.
	Note: After enabling this plugin Deluge may require restarted for it to work properly.
	The events Torrent Complete should be selected and the full path to the script entered 

		/usr/local/deluge/nzbToMedia/TorrentToMedia.py
	
3. Output from TorrentToMedia will be logged where the scripts reside, in a file called "postprocess.log"


### Other Torrent client - BlackHole

If you are using another client this may work as long as you can configure the output parameters for postprocessing.
At minimum we must be able to pass through the torrent downlaod directory.
If you ahve another torrent client and can provide a list of output vriables, please post this under issues and I will try to add your client.
Perform the following steps to configure postprocessing for "TorrentToMedia":

1. Rename the autoProcessMedia.cfg.sample to autoProcessMedia.cfg and edit the parameters:

	i.   [Torrent} uselink = 1 to allow hard-linking of files
		quicker and less harddisk used, if download and final location are on the same hard-disk
		set uselink = 0 to use normal copy options. 
		Any movement across hard disks / network MUST use "0"

	ii.  [Torrent] extractiontool (Windows Only...you will need to install [7-zip](http://www.7-zip.org/ "7-zip"))
		
		C:\Program Files\7-Zip\7z.exe' 
		
	iii. [Torrent] categories: all categories/labels/sub-directories used by your downloader.
		
		music,music_videos,pictures,software
	
	iv.  [Torrent] compressedExtentions: all extensions you want to be identified and extracted
		
		.zip,.rar,.7z,.gz,.bz,.tar,.arj
 	
	v.   [Torrent] mediaExtentions: all extensions you want to be identified as videos and processed.
		
		.mkv,.avi,.divx,.xvid,.mov,.wmv,.mp4,.mpg,.mpeg,.vob,.iso
	
	vi.  [Torrent] metaExtentions: all other extensions you want to be processed. other extensions will be ignored.
		
		.nfo,.sub,.srt,.jpg,.gif

	vii. [CouchPotato] & [SickBeard] category: you must set the category that is passed from these applications
		If using "blackhole-subdirectory", this is the last folder name used in the blackhole.
		
		e.g. tv or movies
		
	viii.[CouchPotato] & [SickBeard] outputDirectory: you must set the absoluet path to extract videos to.
		this destination, for CouchPotato, must match the CouchPotato Renamer's, "from" directory.
		
	ix.  [CouchPotato] & [SickBeard]: 
		Configure the remaining settings as describes in nzbToCouchPotato and nzbToSickBeard above.


2. In your download client, enable the postprocess script and add any output parameters if configurable.
	note: configurable outputs should be set as uTorrent ("utorrent" "directory" "name" "label")
	or deluge ("id" "name" "directory")... "id" can be anything as it is not used.

		/usr/local/nzbToMedia/TorrentToMedia.py
	
3. See the details in the FOLDER STRUCTURE section below to assist with configuration. 
	Please share your results and configurations here or on the couchpota.to forums.

4. Output from TorrentToMedia will be logged where the scripts reside, in a file called "postprocess.log"


### FOLDER STRUCTURE: Important for black-hole and Torrent. 

This is just an example to illustrate how this can be achieved.

Watch Directory / Blackhole
This is the root path where your downloader looks for nzbs/torrents.
This will have 2 sub-directories, "tv" and "movies", which define the "categories".

		/usr/local/blackhole
			/usr/local/blackhole/tv
			/usr/local/blackhole/movies

Download Directory
This is the root path where your downloads are put when finished (and where files will be seeded from for Torrents).
This will have 2 sub-directories, "tv" and "movies", which define the "categories".

		/usr/local/Download
			/usr/local/Download/tv
			/usr/local/Download/movies

destination
This is the directory specified for each category, where final files are moved to after extarction. 
For CouchPotato this will be the renamer "from" directory.
	
		/usr/local/extracted/tv
		/usr/local/extracted/movies
