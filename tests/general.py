import os
import datetime
import re
import nzbtomedia
from nzbtomedia import nzbToMediaDB
from nzbtomedia.nzbToMediaUtil import get_downloadInfo

# Initialize the config
nzbtomedia.initialize()

test = nzbtomedia.CFG['SickBeard','NzbDrone']['tv']
section = nzbtomedia.CFG.findsection('tv').isenabled()
print section