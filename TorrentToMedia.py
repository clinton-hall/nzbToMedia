#!/usr/bin/env python

import autoProcessMovie
import autoProcessTV
import sys, os, ConfigParser, shutil
from subprocess import call

from nzbToMediaEnv import *

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
		print "INFO: Removing empty folder: %s" % (path)
		os.rmdir(path)

old_stdout = sys.stdout #backup the default stdout
log_file = open(os.path.join(os.path.dirname(sys.argv[0]), "postprocess.log"),"a+")
sys.stdout = log_file #create a local log file, and direct all "print" to the log.
print "INFO: TorrentToMedia %s" % VERSION
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
	print "INFO: Script called from utorrent"
	Directory = sys.argv[1]	## %D -- Example output: F:\path\to\dir\My.Series.S01E01.720p.HDTV.x264-2HD
	Name = sys.argv[2]		## %N -- Example output: My.Series.S01E01.720p.HDTV.x264-2HD
	Category = sys.argv[3]	## %L -- Example output: tvseries ## This is the label in uTorrent

elif len(sys.argv) > 1: #Doesn't match Transmission (1) or uTorrent (4).
	print "Error: The number of arguments passed is %s. Unable to determin the arguments to use; Exiting" % (len(sys.argv))
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
		print "INFO: Script called from Transmission"
	except:
		print "Error: There was a problem loading variables from Transmission", "Exiting"
		sys.exit(-1)
	Category = '' #We dont have a category, so assume the last directory is the category for now.
	
print "DEBUG: Received Directory: %s" % (Directory)
print "DEBUG: Received Torrent Name: %s" % (Name)
print "DEBUG: Received Category: %s" % (Category)

status = 0
packed = 0
root = 0
video = 0

config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")

print "INFO: Loading config from %s" % (configFilename)

if not os.path.isfile(configFilename):
	print "ERROR: You need an autoProcessMedia.cfg file - did you rename and edit the .sample?"
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
	print "INFO: Files appear to be in their own directory"
	DirBase2 = os.path.split(os.path.normpath(DirBase[0]))
		if DirBase2[1] == Movie_Cat or DirBase == TV_Cat:
			if not Category:
				print "INFO: Determined Category to be: %s" % (DirBase2[1])
				Category = DirBase2[1]
	
elif DirBase[1] == Movie_Cat or DirBase == TV_Cat:
	if os.path.isdir(os.path.join(Directory, Name)):
		print "INFO: Found torrent directory %s in category directory %s" % (os.path.join(Directory, Name), Directory)
		Directory = os.path.join(Directory, Name)
	else:
		print "INFO: The directory passed is the root directory for category %s" % (DirBase[1])
		print "WARNING: You should change settings to download torrents to their own directory"
		print "INFO: We will try and determine which files to process, individually"
		root = 1
	if not Category:
		print "INFO: Determined Category to be: %s" % (DirBase2[1])
		Category = DirBase[1]
		
else: # no category found in directory. For Utorrent we can do a recursive scan.
	print "INFO: The directory passed does not appear to include a category or the torrent name"
	print "WARNING: You should change settings to download torrents to their own directory"
	print "INFO: We will try and determine which files to process, individually"
	root = 1
		
if Category == Movie_Cat:
	destination = os.path.join(Movie_dest, Name)
elif Category == TV_Cat:
	destination = os.path.join(TV_dest, Name)
else:
	print "INFO: Category of %s does not match either %s or %s: Exiting" %(Category, Movie_Cat, TV_Cat)
	sys.exit(-1)

test = ['.zip', '.rar', '.7z', '.gz', '.bz', '.tar', '.arj']
test2 = ['.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv', '.mp4', '.mpg', '.mpeg']
print "DEBUG: scanning files in directory: %s" % (Directory)
f = [filenames for dirpath, dirnames, filenames in os.walk(Directory)]
if root == 1:
	print "DEBUG: Looking for %s in filenames" % (Name)
	for file in f[1]:
		if (Name in file) or (file in Name):
			if os.path.splitext(file)[1] in test:
				print "INFO: Found a packed file %s" % (file)
				packed = 1
				break
			elif os.path.splitext(file)[1] in test2:
				print "INFO: Found a video file %s" % (file)
				video = 1
				break
			else:
				continue
else:				
	ext = [os.path.splitext(file)[1] for file in f[1]]
	if set(ext).intersection(set(test)):
		print "INFO: Found compressed archives, extracting"
		packed = 1
	## Check that files actully is .mkv / .avi etc, and not packed files or anything else
	elif set(ext).intersection(set(test2)):
		print "INFO: Found media files, moving"
		video = 1
	else:
		print "DEBUG: Found files with extensions %s." % (ext)
		print "DEBUG: Looking for extensions %s or %s." % (test, test2)
		print "INFO: Didn't find any compressed archives or media files to process, exiting"
		sys.exit(-1)

if useLink == 0 and packed == 0 and video == 1: ## copy
	if root == 0: #move all files in tier own directory 
		print "INFO: Copying all files from %s to %s." % (Directory, destination)
		shutil.copytree(Directory, destination)
	else: #we only want to move files matching the torrent name when root directory is used.
		print "INFO: Copying files that match the torrent name %s from %s to %s." % (Name, Directory, destination)
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
	print "INFO: Creating hard link for files from %s to %s." % (Directory, destination)
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
			
			if os.name == 'nt'
				subprocess.call(['cmd', '/C', 'mklink', '/H', source, target], stdout=subprocess.PIPE)
			elif os.name == 'posix':
				os.link(source, target)
			else:
				print "ERROR: Hardlink failed, cannot determine OS."
	
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
				print "ERROR: Unknown file type: %s" % (ext[1])
				continue

		## Create destination folder
		if not os.path.exists(destination):
			try:
				os.makedirs(destination)
			except Exception, e:
				print "ERROR: Not possible to create destination folder: %s" % (e)
				continue

		print"INFO: Extracting to %s" % (destination)
	
		## Running..	
		print "INFO: Extracting %s %s %s %s" % (cmd[0], cmd[1], fp, destination)
		pwd = os.getcwd() # Get our Present Working Directory
		os.chdir(destination) #not all unpack commands accept full paths, so just extract into this directory.
		if os.name == 'nt': #Windows needs quotes around directory structure
			try:
				run = "\"" + cmd[0] + "\" " + cmd[1] + " \"" + fp + "\"" #windows needs quotes around directories.
				res = call(run)
				if res == 0:
					status = 0
					print "INFO: Extraction was successful for %s to %s" % (fp, destination)
				else:
					print "ERROR: Extraction failed for %s. 7zip result was %s" % (fp, res)
			except:
				print "ERROR: Extraction failed for %s. Could not call command %s %s" % (fp, run)
		else:
			try:
				if cmd[1] == "": #if calling unzip, we dont want to pass the ""
					res = call([cmd[0], fp])
				else:
					res = call([cmd[0], cmd[1], fp])
				if res == 0:
					status = 0
					print "INFO: Extraction was successful for %s to %s" % (fp, destination)
				else:
					print "ERROR: Extraction failed for %s. 7zip result was %s" % (fp, res)
			except:
				print "ERROR: Extraction failed for %s. Could not call command %s %s %s %s" % (fp, cmd[0], cmd[1], fp)	
		os.chdir(pwd) # Go back to our Original Working Directory

for dirpath, dirnames, filenames in os.walk(destination): #flatten out the directory to make postprocessing easier.
	if dirpath == destination:
		continue #no need to try and move files in the root destination directory.
	for filename in filenames:
		try:
			shutil.move(os.path.join(dirpath, filename), destination)
		except OSError:
			print "INFO: Could not flatten %s " % (os.path.join(dirpath, filename))
removeEmptyFolders(destination) #cleanup empty directories.

status = int(status)
## Now we pass off to CouchPotato or SickBeard.
if Category == Movie_Cat:  
	autoProcessMovie.process(destination, Name, status)
elif Category == TV_Cat:
	autoProcessTV.processEpisode(destination, Name, status)

sys.stdout = old_stdout #reset our stdout
log_file.close() #close the log
