#! /usr/bin/env python2
import os
import datetime
import re
import nzbtomedia
from nzbtomedia.nzbToMediaAutoFork import autoFork
from nzbtomedia import nzbToMediaDB
from nzbtomedia.nzbToMediaUtil import get_downloadInfo

# Initialize the config
nzbtomedia.initialize()

test = nzbtomedia.CFG['SickBeard','NzbDrone']['tv'].isenabled()
section = nzbtomedia.CFG.findsection('tv').isenabled()
print section
fork, fork_params = autoFork('SickBeard', 'tv')

from babelfish import Language
print Language('eng')

import subliminal

subliminal.cache_region.configure('dogpile.cache.memory')