import os
import datetime
import nzbtomedia
from nzbtomedia import nzbToMediaDB
from nzbtomedia.nzbToMediaUtil import get_downloadInfo

# Initialize the config
nzbtomedia.initialize()

test = nzbtomedia.CFG['HeadPhones']['music']
section = nzbtomedia.CFG.findsection('tv').isenabled()
print section