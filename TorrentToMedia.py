#!/usr/bin/env python

#System imports
import ConfigParser
import logging
import shutil
import sys
import os

# Custom imports
import linktastic.linktastic as linktastic
import autoProcessMovie
import autoProcessTV
from nzbToMediaEnv import *
from nzbToMediaUtil import *


nzbtomedia_configure_logging(os.path.dirname(sys.argv[0]))
Logger = logging.getLogger(__name__)


def removeEmptyFolders(path):
	if not os.path.isdir(path):
		return

	# remove empty subfolders
	files = os.listdir(path)
	if len(files):
		for f in files:
			fullpath = os.path.join(path, f)
			if os.path.isdir(fullpath):
				removeEmptyFolders(fullpath)

	# if folder empty, delete it
	files = os.listdir(path)
	if len(files) == 0:
		Logger.info("Removing empty folder: %s", path)
		os.rmdir(path)


#old_stdout = sys.stdout #backup the default stdout
#log_file = open(os.path.join(os.path.dirname(sys.argv[0]), "postprocess.log"),"a+")
#sys.stdout = log_file #create a local log file, and direct all "print" to the log.
Logger.info("TorrentToMedia %s", VERSION)


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
	Logger.info("Script called from utorrent")
	Directory = sys.argv[1]	## %D -- Example output: F:\path\to\dir\My.Series.S01E01.720p.HDTV.x264-2HD
	Name = sys.argv[2]		## %N -- Example output: My.Series.S01E01.720p.HDTV.x264-2HD
	Category = sys.argv[3]	## %L -- Example output: tvseries ## This is the label in uTorrent

elif len(sys.argv) > 1: #Doesn't match Transmission (1) or uTorrent (4).
	Logger.error("The number of arguments passed is %s. Unable to determin the arguments to use; Exiting", len(sys.argv))
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
		Logger.info("Script called from Transmission")
	except:
		Logger.error("There was a problem loading variables from Transmission: Exiting")
		sys.exit(-1)
	Category = '' #We dont have a category, so assume the last directory is the category for now.

Logger.debug("Received Directory: %s", Directory)
Logger.debug("Received Torrent Name: %s", Name)
Logger.debug("Received Category: %s", Category)

status = 0
packed = 0
root = 0
video = 0

config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")

Logger.info("Loading config from %s", configFilename)

if not os.path.isfile(configFilename):
	Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
	sys.exit(-1)

config.read(configFilename)

TV_Cat = config.get("SickBeard", "category")
TV_dest = config.get("SickBeard", "destination")
Movie_dest = config.get("CouchPotato", "destination")
Movie_Cat = config.get("CouchPotato", "category")
useLink = int(config.get("Torrent", "uselink"))
extractionTool = config.get("Torrent", "extractiontool")

DirBase = os.path.split(os.path.normpath(Directory)) #Test for blackhole sub-directory.
if DirBase[1] == Name:
	Logger.info("Files appear to be in their own directory")
	DirBase2 = os.path.split(os.path.normpath(DirBase[0]))
	if DirBase2[1] == Movie_Cat or DirBase2[1] == TV_Cat:
		if not Category:
			Logger.info("Determined Category to be: %s", DirBase2[1])
			Category = DirBase2[1]

elif DirBase[1] == Movie_Cat or DirBase[1] == TV_Cat:
	if os.path.isdir(os.path.join(Directory, Name)):
		Logger.info("Found torrent directory %s in category directory %s", os.path.join(Directory, Name), Directory)
		Directory = os.path.join(Directory, Name)
	else:
		Logger.info("The directory passed is the root directory for category %s", DirBase[1])
		Logger.warn("You should change settings to download torrents to their own directory")
		Logger.info("We will try and determine which files to process, individually")
		root = 1
	if not Category:
		Logger.info("Determined Category to be: %s", DirBase[1])
		Category = DirBase[1]

else: # no category found in directory. For Utorrent we can do a recursive scan.
	Logger.info("The directory passed does not appear to include a category or the torrent name")
	Logger.warn("You should change settings to download torrents to their own directory")
	Logger.info("We will try and determine which files to process, individually")
	root = 1

if Category == Movie_Cat:
	destination = os.path.join(Movie_dest, Name)
elif Category == TV_Cat:
	destination = os.path.join(TV_dest, Name)
else:
	Logger.info("Category of %s does not match either %s or %s: Exiting", Category, Movie_Cat, TV_Cat)
	sys.exit(-1)

test = ['.zip', '.rar', '.7z', '.gz', '.bz', '.tar', '.arj']
test2 = ['.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv', '.mp4', '.mpg', '.mpeg']
Logger.debug("scanning files in directory: %s", Directory)
f = [filenames for dirpath, dirnames, filenames in os.walk(Directory)]
if root == 1:
	Logger.debug("Looking for %s in filenames", Name)
	for file in f[1]:
		if (Name in file) or (file in Name):
			if os.path.splitext(file)[1] in test:
				Logger.info("Found a packed file %s", file)
				packed = 1
				break
			elif os.path.splitext(file)[1] in test2:
				Logger.info("Found a video file %s", file)
				video = 1
				break
			else:
				continue
else:
	ext = [os.path.splitext(file)[1] for file in f[1]]
	if set(ext).intersection(set(test)):
		Logger.info("Found compressed archives, extracting")
		packed = 1
	## Check that files actully is .mkv / .avi etc, and not packed files or anything else
	elif set(ext).intersection(set(test2)):
		Logger.info("Found media files, moving")
		video = 1
	else:
		Logger.debug("Found files with extensions %s.", ext)
		Logger.debug("Looking for extensions %s or %s.", test, test2)
		Logger.info("Didn't find any compressed archives or media files to process, exiting")
		sys.exit(-1)

if useLink == 0 and packed == 0 and video == 1: ## copy
	if root == 0: #move all files in tier own directory
		Logger.info("Copying all files from %s to %s.", Directory, destination)
		shutil.copytree(Directory, destination)
	else: #we only want to move files matching the torrent name when root directory is used.
		Logger.info("Copying files that match the torrent name %s from %s to %s.", Name, Directory, destination)
		for dirpath, dirnames, filenames in os.walk(Directory):
			for file in filenames:
				if (Name in file) or (file in Name):
					pass
				else:
					continue #ignore the other files
				source = os.path.join(dirpath, file)
				target = os.path.join(destination, file)
				shutil.copy(source, target)

elif useLink == 1 and packed == 0 and video == 1: ## hardlink
	Logger.info("Creating hard link for files from %s to %s.", Directory, destination)
	os.mkdir(destination)
	for dirpath, dirnames, filenames in os.walk(Directory):
		for file in filenames:
			if root == 1: #we only want to move files matching the torrent name when root directory is used.
				if (Name in file) or (file in Name):
					pass
				else:
					continue #ignore the other files
			source = os.path.join(dirpath, file)
			target = os.path.join(destination, file)

			linktastic.link(source, target)

elif packed == 1: ## unpack
	## Using Windows?
	if os.name == 'nt':
		cmd_7zip = [extractionTool, 'x -y']
		ext_7zip = [".rar",".zip",".tar.gz","tgz",".tar.bz2",".tbz",".tar.lzma",".tlz",".7z",".xz"]
		EXTRACT_COMMANDS = dict.fromkeys(ext_7zip, cmd_7zip)
		Logger.info("We are using Windows")

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
		Logger.info("We are using *nix")

	## Need to add a check for which commands that can be utilized in *nix systems..
	else:
		Logger.error("Unknown OS, exiting")

	files = [ f for f in os.listdir(Directory) if os.path.isfile(os.path.join(Directory,f)) ]
	for f in files:
		if root == 1: #we only want to move files matching the torrent name when root directory is used.
			if (Name in file) or (file in Name):
				pass
			else:
				continue #ignore the other files
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
				Logger.debug("Unknown file type: %s", ext[1])
				continue

		## Create destination folder
		if not os.path.exists(destination):
			try:
				os.makedirs(destination)
			except Exception, e:
				Logger.error("Not possible to create destination folder: %s", e)
				continue

		Logger.info("Extracting to %s", destination)

		## Running..
		Logger.info("Extracting %s %s %s %s", cmd[0], cmd[1], fp, destination)
		pwd = os.getcwd() # Get our Present Working Directory
		os.chdir(destination) #not all unpack commands accept full paths, so just extract into this directory.
		if os.name == 'nt': #Windows needs quotes around directory structure
			try:
				run = "\"" + cmd[0] + "\" " + cmd[1] + " \"" + fp + "\"" #windows needs quotes around directories.
				res = call(run)
				if res == 0:
					status = 0
					Logger.info("Extraction was successful for %s to %s", fp, destination)
				else:
					Logger.info("Extraction failed for %s. 7zip result was %s", fp, res)
			except:
				Logger.error("Extraction failed for %s. Could not call command %s %s", fp, run)
		else:
			try:
				if cmd[1] == "": #if calling unzip, we dont want to pass the ""
					res = call([cmd[0], fp])
				else:
					res = call([cmd[0], cmd[1], fp])
				if res == 0:
					status = 0
					Logger.info("Extraction was successful for %s to %s", fp, destination)
				else:
					Logger.error("Extraction failed for %s. 7zip result was %s", fp, res)
			except:
				Logger.error("Extraction failed for %s. Could not call command %s %s %s %s", fp, cmd[0], cmd[1], fp)
		os.chdir(pwd) # Go back to our Original Working Directory

for dirpath, dirnames, filenames in os.walk(destination): #flatten out the directory to make postprocessing easier.
	if dirpath == destination:
		continue #no need to try and move files in the root destination directory.
	for filename in filenames:
		try:
			shutil.move(os.path.join(dirpath, filename), destination)
		except OSError:
			Logger.info("Could not flatten %s", os.path.join(dirpath, filename))
removeEmptyFolders(destination) #cleanup empty directories.

status = int(status)
if status == 0:
	Logger.info("calling autoProcess script for successful download")
else:
	Logger.info("calling autoProcess script for failed download")
## Now we pass off to CouchPotato or SickBeard.
old_stdout = sys.stdout #backup the default stdout
sys.stdout = Logger.info #Capture the print from the autoProcess scripts.
if Category == Movie_Cat:
	autoProcessMovie.process(destination, Name, status)
elif Category == TV_Cat:
	autoProcessTV.processEpisode(destination, Name, status)
sys.stdout = old_stdout #reset our stdout
#log_file.close() #close the log
