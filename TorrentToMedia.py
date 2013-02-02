#!/usr/bin/env python

import autoProcessMovie
import autoProcessTV
import sys, os, ConfigParser
from os import listdir
from os.path import isfile, join


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
	Directory = sys.argv[1]	## %D -- Example output: F:\path\to\dir\My.Series.S01E01.720p.HDTV.x264-2HD
	Name = sys.argv[2]		## %N -- Example output: My.Series.S01E01.720p.HDTV.x264-2HD
	Category = sys.argv[3]	## %L -- Example output: tvseries ## This is the label in uTorrent

else:
	##test for Transmission here.
	print "currently only supports uTorrent. Exiting"
	sys.exit(-1)

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
	destination = Movie_dest
elif Category == TV_Cat:
	destination = TV_dest
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
		EXTRACT_COMMANDS = dict.fromkeys(ext_zip, cmd_7zip)
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

	files = [ f for f in listdir(Directory) if isfile(join(Directory,f)) ]
		for f in files:
			ext = os.path.splitext(f["path"])
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
					
			fp = os.path.join(destination, os.path.normpath(f["path"]))

			## Destination path
			dest = os.path.join(destination, Name)

			## Create destionation folder
			if not os.path.exists(dest):
			try:
				os.makedirs(dest)
			except Exception, e:
				print("ERROR: Not possible to create destination folder: %s", e)
				return

			print("INFO: Extracting to %s", dest)

	
			## Running..	
			print("INFO: Extracting %s %s %s %s", cmd[0], cmd[1], fp, dest)
			d = getProcessValue(cmd[0], cmd[1].split() + [str(fp)], {}, str(dest))
			d.addCallback(on_extract_success)
			d.addErrback(on_extract_failed)

status = int(status)
## Now we pass off to CouchPotato or SickBeard.
if Category == Movie_Cat:  
	autoProcessMovie.process(destination, Name, status)
elif Category == TV_Cat:
	autoProcessTV.processEpisode(destination, Name, status)
    
def on_extract_success(result):
	print("INFO: Extraction was successful for %s")
	status = 0

def on_extract_failed(result):
	print("ERROR: Extraction failed for %s")
