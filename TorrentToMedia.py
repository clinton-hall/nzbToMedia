#!/usr/bin/env python

import sys
import autoProcessMovie
import autoProcessTV
import ConfigParser
import os
from os import listdir
from os.path import isfile, join
import glob


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

## We will pass in %D, %N, %L
Directory = sys.argv[1]	## Example output: F:\path\to\dir\My.Series.S01E01.720p.HDTV.x264-2HD
Name = sys.argv[2]		## Example output: My.Series.S01E01.720p.HDTV.x264-2HD
Category = sys.argv[3]	## Example output: tvseries # this is the label in uTorrent

status = 0
packed = 0
par2 = 0

config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "TorrentToMedia.cfg")

print "transmissionToMedia v 4.1"
print "Loading config from", configFilename

if not os.path.isfile(configFilename):
    print "ERROR: You need an autoProcessMovie.cfg file - did you rename and edit the .sample?"
    sys.exit(-1)

config.read(configFilename)

Movie_Cat = config.get("CouchPotato", "category")
TV_Cat = config.get("SickBeard", "category")

Movie_dest = config.get("CouchPotato", "destination")
TV_dest = config.get("CouchPotato", "destination")

useLink = int(config.get("Torrent", "uselink"))
packed = config.get("Torrent", "packed")
unpacker = config.get("Torrent", "unpacker")

parcheck = config.get("Torrent", "parcheck")

if Category == Movie_Cat:
    destination = Movie_dest
elif Category == TV_Cat:
    destination = TV_dest
else;
    print "Not assigned a label of either", Movie_Cat, "or", TV_Cat, ". Exiting"



test = re.compile('^(.*)\.((zip|rar|7z|gz|bz|tar|arj)|(r[0-9]{1,3})|([0-9]{1,3}))$', re.IGNORECASE|re.UNICODE);
if test.match(destination):
    print "packed files detected"
    packed = 1
	
test = os.path.join(destination, '*.par2')
if glob.glob(test):
    print "par2 files detected"
    par2 = 1

## QUESTION: Do we need this? PAR check is only for usenet?
if par2:
    #parcheck here
    #parcheck

if packed:
	## 7z x test.rar   ---- need to add "yes" to command
	## windows only for now, should be adapted to *nix 
    cmd_7zip = [unpacker, 'x']
    ext_7zip = [".rar",
                ".zip",
                ".tar.gz", "tgz",
                ".tar.bz2", ".tbz",
                ".tar.lzma", ".tlz",
                ".7z", ".xz"]
    EXTRACT_COMMANDS = dict.fromkeys(ext_zip, cmd_7zip)
	print('windows check passed')
	
		files = [ f for f in listdir(Directory) if isfile(join(Directory,f)) ]

        for f in files:
            ext = os.path.splitext(f["path"])
            if ext[1] in (".gz", ".bz2", ".lzma"):
                ## check if this is a tar
                if os.path.splitext(ext[0]) == ".tar":
                    cmd = EXTRACT_COMMANDS[".tar" + ext[1]]
            else:
                if ext[1] in EXTRACT_COMMANDS:
                    cmd = EXTRACT_COMMANDS[ext[1]]
                else:
                    print("unknown file type: %s", ext[1])
                    continue

		fp = os.path.join(save_path, os.path.normpath(f["path"]))

		## destination path
		dest = os.path.join(destination, Name)

		## create destionation folder
        if not os.path.exists(dest):
			try:
				os.makedirs(dest)
					except Exception, e:
					print("cant create destination folder: %s", e)
                    return

		print("extracting to %s", dest)
		def on_extract_success(result):
			print("extract was successful for %s")

		def on_extract_failed(result, torrent_id):
			print("extract failed for %s")
		print("hmm %s %s %s %s", cmd[0], cmd[1], fp, dest)

		## running..
		d = getProcessValue(cmd[0], cmd[1].split() + [str(fp)], {}, str(dest))
		d.addCallback(on_extract_success)
		d.addErrback(on_extract_failed)
else:
	## TODO: Check that files actully is .mkv / .avi etc, and not packed files
	if useLink and packed == 0:
		print "copying all files from", Directory, "to", destination
		shutil.copytree(Directory, destination)
	else:
		print "creating hard link from", Directory, "to", destination
		shutil.copytree(src, dst, copy_function=os.link)

status = int(status)
## Now we pass off to CouchPotato or SickBeard.
if Category == Movie_Cat:  
    autoProcessMovie.process(destination, Name, status)
elif Category == TV_Cat:
    autoProcessTV.processEpisode(destination, Name, status)
