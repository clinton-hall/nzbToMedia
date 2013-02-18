#!/usr/bin/env python

#System imports
import ConfigParser
import sys
import os
import shutil
import logging
import logging.config
from subprocess import call

# Custom imports
import linktastic.linktastic as linktastic
import autoProcessMovie
import autoProcessTV
from nzbToMediaEnv import *

Logger = logging.getLogger()
logFile = os.path.join(os.path.dirname(sys.argv[0]), "postprocess.log")
logging.config.fileConfig(os.path.join(os.path.dirname(sys.argv[0]), "logger.conf"))
fileHandler = logging.FileHandler(logFile, encoding='utf-8', delay=True)
fileHandler.formatter = logging.Formatter('%(asctime)s|%(levelname)-7.7s %(message)s', '%H:%M:%S')
fileHandler.level = logging.DEBUG
Logger.addHandler(fileHandler)

Logger.info("TorrentToMedia %s", VERSION)

config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")

Logger.info("Loading config from %s", configFilename)

if not os.path.isfile(configFilename):
	Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
	sys.exit(-1)

config.read(configFilename)

TV_Cat = config.get("SickBeard", "category")
TV_dest = os.path.normpath(config.get("SickBeard", "destination"))
Movie_dest = os.path.normpath(config.get("CouchPotato", "destination"))
Movie_Cat = config.get("CouchPotato", "category")
useLink = int(config.get("Torrent", "uselink"))
extractionTool = config.get("Torrent", "extractiontool")

def category_search(Directory, Category, root):
	DirBase = os.path.split(os.path.normpath(Directory)) #Test for blackhole sub-directory.
	if DirBase[1] == Name:
		Logger.info("Files appear to be in their own directory")
		DirBase2 = os.path.split(os.path.normpath(DirBase[0]))
		if DirBase2[1] == Movie_Cat or DirBase2[1] == TV_Cat:
			if not Category:
				Logger.info("Determined Category to be: %s", DirBase2[1])
				Category = DirBase2[1]
		elif not Category:
			Logger.error("Could not identify category from the directory structure. please check downlaoder settings.")
			sys.exit(-1)
		else:
			pass
		
	elif DirBase[1] == Movie_Cat or DirBase[1] == TV_Cat:
		if os.path.isdir(os.path.join(Directory, Name)):
			Logger.info("Found torrent directory %s in category directory %s", os.path.join(Directory, Name), Directory)
			Directory = os.path.join(Directory, Name)
		else:
			Logger.info("The directory passed is the root directory for category %s", DirBase[1])
			Logger.warn("You should change settings to download torrents to their own directory if possible")
			Logger.info("We will try and determine which files to process, individually")
			root = 1
		if not Category:
			Logger.info("Determined Category to be: %s", DirBase[1])
			Category = DirBase[1]
	elif not Category:
		Logger.error("Could not identify category from the directory structure. please check downlaoder settings.")
		sys.exit(-1)
	else:
		Logger.info("The directory passed does not appear to include a category or the torrent name")
		Logger.warn("You should change settings to download torrents to their own directory if possible and include Label/Category directories.")
		Logger.info("We will try and determine which files to process, individually")
		root = 1
	return Directory, Category, root 

def is_sample(file_path, Name):
	# 200 MB in bytes
	SIZE_CUTOFF = 200 * 1024 * 1024
	# ignore 'sample' in files unless 'sample' in Torrent Name
	if ('sample' in file_path.lower()) and (not 'sample' in Name) and (os.path.getsize(file_path) < SIZE_CUTOFF):
		return True
	else:
		return False

def copy_link(source, target, useLink, destination):
	## Create destination folder
	if not os.path.exists(destination):
		try:
			Logger.debug("Creating destination folder: %s", destination)
			os.makedirs(destination)
		except Exception, e:
			Logger.error("Not possible to create destination folder: %s", e)
			return False
	if useLink:
		try:
			Logger.debug("Linking %s to %s", source, target)
			linktastic.link(source, target)
		except:
			if os.path.isfile(target):
				Logger.info("something went wrong in linktastic.link, but the destination file was created")
			else:
				Logger.info("something went wrong in linktastic.link. trying to create a copy")
				Logger.debug("Copying %s to %s", source, target)
				shutil.copy(source, target)
	else:
		Logger.debug("Copying %s to %s", source, target)
		shutil.copy(source, target)
	return True

def unpack(dirpath, file, destination):
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

	ext = os.path.splitext(file)
	fp = os.path.join(dirpath, file)
	if ext[1] in (".gz", ".bz2", ".lzma"):
	## Check if this is a tar
		if os.path.splitext(ext[0])[1] == ".tar":
			cmd = EXTRACT_COMMANDS[".tar" + ext[1]]
	else:
		if ext[1] in EXTRACT_COMMANDS:
			cmd = EXTRACT_COMMANDS[ext[1]]
		else:
			Logger.debug("Unknown file type: %s", ext[1])
			return False

	## Create destination folder
	if not os.path.exists(destination):
		try:
			Logger.debug("Creating destination folder: %s", destination)
			os.makedirs(destination)
		except Exception, e:
			Logger.error("Not possible to create destination folder: %s", e)
			return False

	Logger.info("Extracting %s to %s", fp, destination)

	## Running..	
	Logger.debug("Extracting %s %s %s %s", cmd[0], cmd[1], fp, destination)
	pwd = os.getcwd() # Get our Present Working Directory
	os.chdir(destination) #not all unpack commands accept full paths, so just extract into this directory.
	if os.name == 'nt': #Windows needs quotes around directory structure
		try:
			run = "\"" + cmd[0] + "\" " + cmd[1] + " \"" + fp + "\"" #windows needs quotes around directories.
			res = call(run)
			if res == 0:
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
				Logger.info("Extraction was successful for %s to %s", fp, destination)
			else:
				Logger.error("Extraction failed for %s. 7zip result was %s", fp, res)
		except:
			Logger.error("Extraction failed for %s. Could not call command %s %s %s %s", fp, cmd[0], cmd[1], fp)	
	os.chdir(pwd) # Go back to our Original Working Directory
	return True

def flatten(destination):
	Logger.info("Flattening directory: %s", destination)
	for dirpath, dirnames, filenames in os.walk(destination): #flatten out the directory to make postprocessing easier.
		if dirpath == destination:
			continue #no need to try and move files in the root destination directory.
		for filename in filenames:
			try:
				shutil.move(os.path.join(dirpath, filename), destination)
			except OSError:
				Logger.info("Could not flatten %s", os.path.join(dirpath, filename))
	removeEmptyFolders(destination) #cleanup empty directories.

def removeEmptyFolders(path):
	Logger.info("Removing empty folders in: %s", path)
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
		Logger.debug("Removing empty folder: %s", path)
		os.rmdir(path)

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
	Directory = os.path.normpath(sys.argv[1])	## %D -- Example output: F:\path\to\dir\My.Series.S01E01.720p.HDTV.x264-2HD
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
		Directory = os.path.normpath(os.getenv('TR_TORRENT_DIR'))
		Name = os.getenv('TR_TORRENT_NAME')
		Logger.info("Script called from Transmission")
	except:
		Logger.error("There was a problem loading variables from Transmission: Exiting")
		sys.exit(-1)
	Category = '' #We dont have a category, so assume the last directory is the category for now.
	
Logger.debug("Received Directory: %s", Directory)
Logger.debug("Received Torrent Name: %s", Name)
Logger.debug("Received Category: %s", Category)

status = 1 # we start as "failed" until we verify movie file in destination
root = 0
video = 0
video2 = 0

Directory, Category, root = category_search(Directory, Category, root) # confirm the catgeogy by parsing directory structure.
		
if Category == Movie_Cat:
	destination = os.path.join(Movie_dest, Name)
elif Category == TV_Cat:
	destination = os.path.join(TV_dest, Name)
else:
	Logger.info("Category of %s does not match either %s or %s: Exiting", Category, Movie_Cat, TV_Cat)
	sys.exit(-1)

packed_files = ['.zip', '.rar', '.7z', '.gz', '.bz', '.tar', '.arj']
video_files = ['.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv', '.mp4', '.mpg', '.mpeg', '.vob', '.iso']
meta_files = ['.nfo', '.sub', '.srt', '.jpg', '.gif']
Logger.debug("scanning files in directory: %s", Directory)

for dirpath, dirnames, filenames in os.walk(Directory):
	for file in filenames:
		if root == 1:
			Logger.debug("Looking for %s in filename", Name)
			if (Name in file) or (file in Name):
				pass #This file does match the Torrent name
			else:
				continue #This file does not match the Torrent name. Skip it
		file_path = os.path.join(dirpath, file)
		file_ext = os.path.splitext(file)[1]
		if file_ext in video_files: #if the file is a video file.
			if is_sample(file_path, Name):
				Logger.info("file %s is a sample file. Ignoring", file_path)
				continue #ignore samples
			video = video + 1
			source = file_path
			target = os.path.join(destination, file)
			Logger.info("Found video file %s.", file)
			state = copy_link(source, target, useLink, destination)
			if state == False:
				Logger.info("Failed to link file %s.", file)
		elif file_ext in meta_files:
			source = file_path
			target = os.path.join(destination, file)
			Logger.info("Found metadata file %s.", file)
			state = copy_link(source, target, useLink, destination)
			if state == False:
				Logger.info("Failed to link file %s.", file)
		elif file_ext in packed_files:
			Logger.info("Found packed file %s.", file)
			source = file_path
			target = os.path.join(destination, file)
			state = unpack(dirpath, file, destination)
			if state == False:
				Logger.info("Failed to unpack file %s.", file)
		else:
			Logger.info("Unknown file type %s for file %s. Ignoring", file_ext, file_path)
			continue
flatten(destination)

#now check if movie files exist in destination:
for dirpath, dirnames, filenames in os.walk(destination):
	for file in filenames:
		file_path = os.path.join(dirpath, file)
		file_ext = os.path.splitext(file)[1]
		if file_ext in video_files: #if the file is a video file.
			video2 = video2 + 1
if video2 >= video and video2 > 0:	#check that all video files were moved.		
	status = 0

status = int(status)
if status == 0:
	Logger.info("calling autoProcess script for successful download")
else:
	Logger.info("calling autoProcess script for failed download")
## Now we pass off to CouchPotato or SickBeard.
# still need to figure out how to log this output.
if Category == Movie_Cat:  
	autoProcessMovie.process(destination, Name, status)
elif Category == TV_Cat:
	autoProcessTV.processEpisode(destination, Name, status)
