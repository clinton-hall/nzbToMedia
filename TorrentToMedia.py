#!/usr/bin/env python

import autoProcessMovie
import autoProcessTV
import sys, os, ConfigParser
from subprocess import call

old_stdout = sys.stdout #backup the default stdout
log_file = open(os.path.join(os.path.dirname(sys.argv[0]), "postprocess.log"),"a+")
sys.stdout = log_file #create a local log file, and direct all "print" to the log.
print "TorrentToMedia V4.1"
if len(sys.argv) == 4:
	##You can use the following parameters (UTORRENT):
	##
	##%F - Name of downloaded file (for single file torrents)
	##%D - Directory where files are saved
	##%N - Title of torrent
	##%P - Previous state of torrent
	##%L - Label
	##%T - Tracker
	##%M - Status message string (same as status column)
	##%I - hex encoded info-hash
	##%S - State of torrent
	##%K - kind of torrent (single|multi)
	##
	##Where State is one of:
	##
	##Error - 1
	##Checked - 2
	##Paused - 3
	##Super seeding - 4
	##Seeding - 5
	##Downloading - 6
	##Super seed [F] - 7
	##Seeding [F] - 8
	##Downloading [F] - 9
	##Queued seed - 10
	##Finished - 11
	##Queued - 12
	##Stopped - 13
	
	## We will pass in %D, %N, %L from uTorrent
	print "script called from utorrent"
	Directory = sys.argv[1]	## %D -- Example output: F:\path\to\dir\My.Series.S01E01.720p.HDTV.x264-2HD
	Name = sys.argv[2]		## %N -- Example output: My.Series.S01E01.720p.HDTV.x264-2HD
	Category = sys.argv[3]	## %L -- Example output: tvseries ## This is the label in uTorrent

elif len(sys.argv) > 1: #Doesn't match Transmission (1) or uTorrent (4).
	print "The number of arguments passed is", len(sys.argv), "unable to determin the arguments to use, Exiting"
	sys.exit(-1)

else:
	##test for Transmission here.
	#TR_APP_VERSION
	#TR_TIME_LOCALTIME
	#TR_TORRENT_DIR
	#TR_TORRENT_HASH
	#TR_TORRENT_ID
	#TR_TORRENT_NAME
	try:
		Directory = os.getenv('TR_TORRENT_DIR')
		Name = os.getenv('TR_TORRENT_NAME')
		print "script called from Transmission"
	except:
		print "There was a problem loading variables from Transmission", "Exiting"
		sys.exit(-1)
	Category = os.path.basename(os.path.normpath(Directory)) #We assume the last directory is the category for now.
	
if not Category:
	Category = os.path.basename(os.path.normpath(Directory)) #Test for blackhole sub-directory.

status = 0
packed = 0

config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")

print "INFO: Loading config from", configFilename

if not os.path.isfile(configFilename):
	print "ERROR: You need an autoProcessMedia.cfg file - did you rename and edit the .sample?"
	sys.exit(-1)

config.read(configFilename)

TV_Cat = config.get("SickBeard", "category")
TV_dest = config.get("CouchPotato", "destination")
Movie_dest = config.get("CouchPotato", "destination")
Movie_Cat = config.get("CouchPotato", "category")
useLink = int(config.get("Torrent", "uselink"))
extractionTool = config.get("Torrent", "extractiontool")

if Category == Movie_Cat:
	destination = os.path.join(Movie_dest, Name)
elif Category == TV_Cat:
	destination = os.path.join(TV_dest, Name)
else:
	print "INFO: Not assigned a label of either", Movie_Cat, "or", TV_Cat, ". Exiting"
	sys.exit(-1)

test = re.compile('^(.*)\.((zip|rar|7z|gz|bz|tar|arj)|(r[0-9]{1,3})|([0-9]{1,3}))$', re.IGNORECASE|re.UNICODE);
test2 = re.compile('^(.*)\.(mkv|avi|divx|xvid|mov|wmv)$', re.IGNORECASE|re.UNICODE);
if test.match(Directory):
	print "INFO: Found compressed archives, extracting"
	packed = 1
## Check that files actully is .mkv / .avi etc, and not packed files or anything else
elif test2.match(Directory):
	print "INFO: Found media files, moving"
else:
	print "INFO: Didn't find any compressed archives or media files to process, exiting"
	sys.exit(-1)

if useLink == 0 and packed == 0: ## copy
	print "INFO: Copying all files from", Directory, "to", destination
	shutil.copytree(Directory, destination)

elif useLink == 1 and packed == 0: ## hardlink
	print "INFO: Creating hard link from", Directory, "to", destination
	shutil.copytree(Directory, destination, copy_function=os.link)
	
elif packed == 1: ## unpack
	## Using Windows?
	if os.name == 'nt':
		cmd_7zip = [extractionTool, 'x -y']
		ext_7zip = [".rar",".zip",".tar.gz","tgz",".tar.bz2",".tbz",".tar.lzma",".tlz",".7z",".xz"]
		EXTRACT_COMMANDS = dict.fromkeys(ext_7zip, cmd_7zip)
		print "INFO: We are using Windows"
		
	## Using linux?
	elif os.name == 'posix':
		required_cmds=["unrar", "unzip", "tar", "unxz", "unlzma", "7zr"]
		EXTRACT_COMMANDS = {
		".rar": ["unrar", "x -o+ -y"],
		".zip": ["unzip", ""],
		".tar.gz": ["tar", "xzf"],
		".tgz": ["tar", "xzf"],
		".tar.bz2": ["tar", "xjf"],
		".tbz": ["tar", "xjf"],
		".tar.lzma": ["tar", "--lzma xf"],
		".tlz": ["tar", "--lzma xf"],
		".txz": ["tar", "--xz xf"],
		".7z": ["7zr", "x"],
		}
		print "INFO: We are using *nix"
		
	## Need to add a check for which commands that can be utilized in *nix systems..
	else:
		print "ERROR: Unknown OS, exiting"

	files = [ f for f in os.listdir(Directory) if os.path.isfile(os.path.join(Directory,f)) ]
		for f in files:
			ext = os.path.splitext(f)
			fp = os.path.join(Directory, os.path.normpath(f))
			if ext[1] in (".gz", ".bz2", ".lzma"):
			## Check if this is a tar
				if os.path.splitext(ext[0])[1] == ".tar":
					cmd = EXTRACT_COMMANDS[".tar" + ext[1]]
			else:
				if ext[1] in EXTRACT_COMMANDS:
					cmd = EXTRACT_COMMANDS[ext[1]]
				else:
					print("ERROR: Unknown file type: %s", ext[1])
					continue

			## Create destination folder
			if not os.path.exists(destination):
			try:
				os.makedirs(destination)
			except Exception, e:
				print("ERROR: Not possible to create destination folder: %s", e)
				return

			print("INFO: Extracting to %s", destination)

	
			## Running..	
			print("INFO: Extracting %s %s %s %s", cmd[0], cmd[1], fp, destination)
			pwd = os.getcwd # Get our Present Working Directory
			os.chdir(destination) #not all unpack commands accept full paths, so just extract into this directory.
			if os.name == 'nt': #Windows needs quotes around directory structure
				try:
					run = "\"" + cmd[0] + "\" " + cmd[1] + " \"" + fp + "\"" #windows needs quotes around directories.
					res = call(run)
					if res == 0:
						status = 0
						print ("INFO: Extraction was successful for %s to %s", fp, destination)
					else:
						print("ERROR: Extraction failed for %s. 7zip result was %s", fp, res)
				except:
					print ("ERROR: Extraction failed for %s. Could not call command %s %s", fp, run)
			else:
				try:
					if cmd[1] == "": #if calling unzip, we dont want to pass the ""
						res = call([cmd[0], fp])
					else:
						res = call([cmd[0], cmd[1], fp])
					if res == 0:
						status = 0
						print ("INFO: Extraction was successful for %s to %s", fp, destination)
					else:
						print("ERROR: Extraction failed for %s. 7zip result was %s", fp, res)
				except:
					print ("ERROR: Extraction failed for %s. Could not call command %s %s %s %s", fp, cmd[0], cmd[1], fp)	
			os.chdir(pwd) # Go back to our Original Working Directory
				
status = int(status)
## Now we pass off to CouchPotato or SickBeard.
if Category == Movie_Cat:  
	autoProcessMovie.process(destination, Name, status)
elif Category == TV_Cat:
	autoProcessTV.processEpisode(destination, Name, status)

sys.stdout = old_stdout #reset our stdout
log_file.close() #close the log
