#! /usr/bin/env python2
import os
import datetime
import re
import nzbtomedia
from nzbtomedia.nzbToMediaAutoFork import autoFork
from nzbtomedia import nzbToMediaDB
from nzbtomedia.nzbToMediaUtil import get_downloadInfo, server_responding

# Initialize the config
nzbtomedia.initialize()

test = nzbtomedia.CFG['SickBeard','NzbDrone']['tv'].isenabled()
section = nzbtomedia.CFG.findsection('tv').isenabled()
print section
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
print Language('eng')

import subliminal

subliminal.cache_region.configure('dogpile.cache.memory')