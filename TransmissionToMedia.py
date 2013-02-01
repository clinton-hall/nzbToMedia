#!/usr/bin/env python

import sys
import autoProcessMovie
import autoProcessTV
import ConfigParser
import os
import glob

##You can use the following parameters:
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
Directory = sys.argv[1]
Name = sys.argv[2]
Categoty = sys.argv[3]
print "transmissionToMedia v 4.0"

config = ConfigParser.ConfigParser()
configFilename = os.path.join(os.path.dirname(sys.argv[0]), "TransmissionToMedia.cfg")

print "Loading config from", configFilename

if not os.path.isfile(configFilename):
    print "ERROR: You need an autoProcessMovie.cfg file - did you rename and edit the .sample?"
    sys.exit(-1)

config.read(configFilename)

Movie_Cat = config.get("CouchPotato", "category")
TV_Cat = config.get("SickBeard", "category")
Movie_dest = config.get("CouchPotato", "destination")
TV_dest = config.get("CouchPotato", "destination")
Use_cp = int(config.get("Transmission", "copy"))
unrar = config.get("Transmission", "unrar")
unzip = config.get("Transmission", "unzip")
parcheck = config.get("Transmission", "parcheck")

if Category == Movie_Cat:
    destination = Movie_dest
elif Category == TV_Cat:
    destination = TV_dest
else;
    print "Not assigned a label of either", Movie_Cat, "or", TV_Cat, ". Exiting"

if Use_cp:
    print "copying all files from", Directory, "to", destination
    shutil.copytree(Directory, destination)
else:
    print "creating hard link from", Directory, "to", destination
    shutil.copytree(src, dst, copy_function=os.link)

status = 0
rared = 0
par2 = 0
ziptest = 0
test = os.path.join(destination, '*.rar')
if glob.glob(test):
    print "rar files detected"
    rared = 1
    #status = 1
test = os.path.join(destination, '*.par2')
if  glob.glob(test):
    print "par2 files detected"
    par2 = 1
test = os.path.join(destination, '*.zip')
if  glob.glob(test):
    print "zip files detected"
    ziped = 1
    #status = 1
if ziped:
    #unzip here and reset status to 0 is successful
    #unzip
if par2:
    #parcheck here
    #parcheck
if rared:
    #unrar here and reset status to 0 if successful
    #unrar
status = 0

status = int(status)
##Now we pass off to CouchPotato or SickBeard.
if Category == Movie_Cat:  
    autoProcessMovie.process(destination, Name, status)
elif Category == TV_Cat:
    autoProcessTV.processEpisode(destination, Name, status)
