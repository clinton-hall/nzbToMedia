#! /usr/bin/env python2
import os
import sys
import datetime
import re
import core
from core.nzbToMediaAutoFork import autoFork
from core import nzbToMediaDB
from core.transcoder import transcoder
from core.nzbToMediaUtil import get_downloadInfo, server_responding

# Initialize the config
core.initialize()

#label = core.TORRENT_CLASS.core.get_torrent_status("f33a9c4b15cbd9170722d700069af86746817ade", ["label"]).get()['label']
#print label

if transcoder.isVideoGood(core.TEST_FILE, 0):
    print "FFPROBE Works"
else:
    print "FFPROBE FAILED"

test = core.CFG['SickBeard','NzbDrone']['tv'].isenabled()
print test
section = core.CFG.findsection('tv').isenabled()
print section
print len(section)
fork, fork_params = autoFork('SickBeard', 'tv')

if server_responding("http://127.0.0.1:5050"):
    print "CouchPotato Running"
if server_responding("http://127.0.0.1:7073"):
    print "SickBeard Running"
if server_responding("http://127.0.0.1:8181"):
    print "HeadPhones Running"
if server_responding("http://127.0.0.1:8085"):
    print "Gamez Running"
if server_responding("http://127.0.0.1:8090"):
    print "Mylar Running"

from babelfish import Language
lan = 'pt'
lan = Language.fromalpha2(lan)
print lan.alpha3

import subliminal

subliminal.cache_region.configure('dogpile.cache.memory')
del core.MYAPP