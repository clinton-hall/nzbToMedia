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
import UnRAR2
from UnRAR2.rar_exceptions import *
import autoProcessMovie
import autoProcessTV
from nzbToMediaEnv import *

Logger = logging.getLogger()
logFile = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), "postprocess.log"))
logging.config.fileConfig(os.path.join(os.path.dirname(sys.argv[0]), "logger.conf"))
fileHandler = logging.FileHandler(logFile, encoding='utf-8', delay=True)
fileHandler.formatter = logging.Formatter('%(asctime)s|%(levelname)-7.7s %(message)s', '%H:%M:%S')
fileHandler.level = logging.DEBUG
Logger.addHandler(fileHandler)


def cleanup(outputDestination):
	for path, dirs, files in os.walk(outputDestination):
		for fn in files:
			os.remove(os.path.join(path, fn))
		for dir in dirs:
			os.removedirs(os.path.join(path, dir))

def category_search(inputDirectory, inputCategory, root):
	categorySearch = os.path.split(os.path.normpath(inputDirectory)) # Test for blackhole sub-directory
	if categorySearch[1] == inputName:
		Logger.info("SEARCH: Files appear to be in their own directory")
		categorySearch2 = os.path.split(os.path.normpath(categorySearch[0]))
		if categorySearch2[1] == movieCategory or categorySearch2[1] == tvCategory:
			if not inputCategory:
				Logger.info("SEARCH: Determined Category to be: %s", categorySearch2[1])
				inputCategory = categorySearch2[1]
		elif not inputCategory:
			Logger.error("SEARCH: Could not identify category from the directory structure. please check downlaoder settings")
			sys.exit(-1)
		else:
			pass
		
	elif categorySearch[1] == movieCategory or categorySearch[1] == tvCategory:
		if os.path.isdir(os.path.join(inputDirectory, inputName)):
			Logger.info("SEARCH: Found torrent directory %s in category directory %s", os.path.join(inputDirectory, inputName), inputDirectory)
			inputDirectory = os.path.join(inputDirectory, inputName)
		else:
			Logger.info("SEARCH: The directory passed is the root directory for category %s", categorySearch[1])
			Logger.warn("SEARCH: You should change settings to download torrents to their own directory if possible")
			Logger.info("SEARCH: We will try and determine which files to process, individually")
			root = 1
		if not inputCategory:
			Logger.info("SEARCH: Determined Category to be: %s", categorySearch[1])
			inputCategory = categorySearch[1]
	elif not inputCategory:
		Logger.error("SEARCH: Could not identify category from the directory structure. please check downlaoder settings")
		sys.exit(-1)
	else:
		Logger.info("SEARCH: The directory passed does not appear to include a category or the torrent name")
		Logger.warn("SEARCH: You should change settings to download torrents to their own directory if possible and include Label/Category directories")
		Logger.info("SEARCH: We will try and determine which files to process, individually")
		root = 1
	return inputDirectory, inputCategory, root 

def is_sample(filePath, inputName):
	# 200 MB in bytes
	SIZE_CUTOFF = 200 * 1024 * 1024
	# Ignore 'sample' in files unless 'sample' in Torrent Name
	if ('sample' in filePath.lower()) and (not 'sample' in inputName) and (os.path.getsize(filePath) < SIZE_CUTOFF):
		return True
	else:
		return False

def copy_link(source, target, useLink, outputDestination):
	# Create destination folder
	if not os.path.exists(outputDestination):
		try:
			Logger.debug("COPYLINK: Creating destination folder: %s", outputDestination)
			os.makedirs(outputDestination)
		except Exception, e:
			Logger.error("COPYLINK: Not possible to create destination folder: %s", e)
			return False

	if useLink:
		try:
			Logger.debug("COPYLINK: Linking %s to %s", source, target)
			linktastic.link(source, target)
		except:
			if os.path.isfile(target):
				Logger.info("COPYLINK: Something went wrong in linktastic.link, but the destination file was created")
			else:
				Logger.info("COPYLINK: Something went wrong in linktastic.link, copying instead")
				Logger.debug("COPYLINK: Copying %s to %s", source, target)
				shutil.copy(source, target)
	else:
		Logger.debug("Copying %s to %s", source, target)
		shutil.copy(source, target)
	return True

def unpack(dirpath, file, outputDestination):
# Create destination folder
	if not os.path.exists(outputDestination):
		try:
			Logger.debug("EXTRACTOR: Creating destination folder: %s", outputDestination)
			os.makedirs(outputDestination)
		except Exception, e:
			Logger.error("EXTRACTOR: Not possible to create destination folder: %s", e)
			return False
	path = os.path.join(dirpath, file)
	try:
		archive = UnRAR2.RarFile(path)
		for rarinfo in archive.infoiter():
			name = rarinfo.filename
			archive.extract(name, outputDestination)
			Logger.error("EXTRACTOR: Files extracted from %s to %s", path, outputDestination)
	except Exception, e:
		Logger.error("EXTRACTOR: Extraction process failed: %s", e)
		sys.exit(-1)
	return True

def flatten(outputDestination):
	Logger.info("FLATTEN: Flattening directory: %s", outputDestination)
	for dirpath, dirnames, filenames in os.walk(outputDestination): #flatten out the directory to make postprocessing easier
		if dirpath == outputDestination:
			continue # No need to try and move files in the root destination directory
		for filename in filenames:
			source = os.path.join(dirpath, filename)
			if not os.path.exists(source):
				try:
					shutil.move(source, outputDestination)
				except OSError:
					Logger.info("FLATTEN: Could not flatten %s", source)
			else:
				Logger.info("FLATTEN: Could not flatten %s", source)
	removeEmptyFolders(outputDestination) # Cleanup empty directories

def removeEmptyFolders(path):
	Logger.info("REMOVER: Removing empty folders in: %s", path)
	if not os.path.isdir(path):
		return

	# Remove empty subfolders
	files = os.listdir(path)
	if len(files):
		for f in files:
			fullpath = os.path.join(path, f)
			if os.path.isdir(fullpath):
				removeEmptyFolders(fullpath)

	# If folder empty, delete it
	files = os.listdir(path)
	if len(files) == 0:
		Logger.debug("REMOVER: Removing empty folder: %s", path)
		os.rmdir(path)

Logger.info("TorrentToMedia %s", VERSION)
config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")


### TORREN TO MEDIA ###
if not os.path.isfile(configFilename):
	Logger.error("You need an autoProcessMedia.cfg file - did you rename and edit the .sample?")
	sys.exit(-1)
else:
	Logger.info("MAIN: Loading config from %s", configFilename)
	config.read(configFilename)

	if len(sys.argv) == 3 or os.getenv('TR_TORRENT_DIR') != '':
		# We will pass in %D, %N from uTorrent, or %TR_TORRENT_DIR% %TR_TORRENT_NAME% from Transmission
		# In short pass "/path/to/downloaded/torrent/ name" to TorrentToMedia.py, eg  >>>> TorrentToMedia.py /Downloaded/MovieName.2013.BluRay.1080p.x264-10bit.DTS MovieName.2013.BluRay.1080p.x264-10bit.DTS <<<<
		if os.getenv('TR_TORRENT_DIR') != '':
			inputDirectory = os.path.normpath(os.getenv('TR_TORRENT_DIR'))
			inputName = os.getenv('TR_TORRENT_NAME')
		else:
			inputDirectory = os.path.normpath(sys.argv[1])
			inputName = sys.argv[2]
		inputCategory = '' # We dont have a category yet
		Logger.debug("MAIN: Received Directory: %s | Name: %s", inputDirectory, inputName)

		# Sick-Beard
		tvCategory = config.get("SickBeard", "category")
		tvDestination = os.path.normpath(config.get("SickBeard", "outputDirectory"))
		# CouchPotatoServer
		movieCategory = config.get("CouchPotato", "category")
		movieDestination = os.path.normpath(config.get("CouchPotato", "outputDirectory"))
		# Torrent specific
		useLink = int(config.get("Torrent", "useLink"))
		extractionTool = os.path.normpath(config.get("Torrent", "extractionTool"))
		compressedContainer = config.get("Torrent", "compressedExtentions")
		mediaContainer = config.get("Torrent", "mediaExtentions")
		metaContainer = config.get("Torrent", "metaExtentions")

		status = int(1) # We start as "failed" until we verify movie file in destination
		root = int(0)
		video = int(0)
		video2 = int(0)

		inputDirectory, inputCategory, root = category_search(inputDirectory, inputCategory, root) # Confirm the catgeogy by parsing directory structure
		if inputCategory == movieCategory:
			outputDestination = os.path.normpath(os.path.join(movieDestination, inputName))
		elif inputCategory == tvCategory:
			outputDestination = os.path.normpath(os.path.join(tvDestination, inputName))
		else:
			Logger.error("MAIN: Category of %s does not match either %s or %s: Exiting", inputCategory, movieCategory, tvCategory)
			sys.exit(-1)

		Logger.debug("MAIN: Scanning files in directory: %s", inputDirectory)
		for dirpath, dirnames, filenames in os.walk(inputDirectory):
			for file in filenames:
				if root == 1:
					Logger.debug("MAIN: Looking for %s in filename", inputName)
					if (inputName in file) or (os.path.splitext(file)[0] in inputName):
						pass # This file does match the Torrent name
						logger.debug("Found file %s that matches Torrent Name %s", file, inputName)
					else:
						continue # This file does not match the Torrent name, skip it
				filePath = os.path.join(dirpath, file)
				fileExtention = os.path.splitext(file)[1]
				if fileExtention in mediaContainer: # If the file is a video file
					if is_sample(filePath, inputName): # Ignore samples
						Logger.info("MAIN: Ignoring %s  sample file. Ignoring", filePath)
						continue 
					else:
						video = video + 1
						source = filePath
						target = os.path.join(outputDestination, file)
						Logger.info("MAIN: Found video file %s in %", fileExtention, filePath)
						state = copy_link(source, target, useLink, outputDestination)
						if state == False:
							Logger.info("MAIN: Failed to link file %s", file)
				elif fileExtention in metaContainer:
					source = filePath
					target = os.path.join(outputDestination, file)
					Logger.info("MAIN: Found metadata file %s for file %s", fileExtention, filePath)
					state = copy_link(source, target, useLink, outputDestination)
					if state == False:
						Logger.info("MAIN: Failed to link file %s", file)
				elif fileExtention in compressedContainer:
					Logger.info("MAIN: Found compressed archive %s for file %s", fileExtention, filePath)
					source = filePath
					target = os.path.join(outputDestination, file)
					state = unpack(dirpath, file, outputDestination)
					if state == False:
						Logger.info("MAIN: Failed to unpack file %s", file)
				else:
					Logger.info("MAIN: Ignoring unknown filetype %s for file %s", fileExtention, filePath)
					continue
		flatten(outputDestination)

		# Now check if movie files exist in destination:
		for dirpath, dirnames, filenames in os.walk(outputDestination):
			for file in filenames:
				filePath = os.path.join(dirpath, file)
				fileExtention = os.path.splitext(file)[1]
				if fileExtention in mediaContainer: # If the file is a video file
					if is_sample(file_path, Name):
						Logger.info("file %s is a sample file. Removing", file_path)
						os.unlink(file_path) #remove samples
					else:
						video2 = video2 + 1
		if video2 >= video and video2 > 0: # Check that all video files were moved
			status = 0
			
		if status == 0:
			Logger.info("MAIN: Successful run")
			# Now we pass off to CouchPotato or Sick-Beard
			## log this output.
			old_stdout = sys.stdout  ## Still crude, but we wat to capture this for now.
			log_file = open(logFile,"a+")
			sys.stdout = log_file
			if inputCategory == movieCategory:  
				Logger.info("MAIN: Calling postprocessing script for CouchPotatoServer")
				autoProcessMovie.process(outputDestination, inputName, status)
			elif inputCategory == tvCategory:
				Logger.info("MAIN: Calling postprocessing script for Sick-Beard")
				autoProcessTV.processEpisode(outputDestination, inputName, status)
			sys.stdout = old_stdout
			log_file.close()
		else:
			Logger.info("MAIN: Something failed! :(")
	else:
		Logger.error("MAIN: There was a problem loading variables: Exiting")
		sys.exit(-1)