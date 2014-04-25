import os
import datetime
import re
import nzbtomedia
from nzbtomedia import nzbToMediaDB
from nzbtomedia.nzbToMediaUtil import get_downloadInfo

# Initialize the config
nzbtomedia.initialize()

EXTENSIONS = [re.compile('.r\d{2}$', re.I),
              re.compile('.part\d+.rar$', re.I),
              re.compile('.rar$', re.I)]
EXTENSIONS += [re.compile('%s$' % ext, re.I) for ext in nzbtomedia.COMPRESSEDCONTAINER]

test = nzbtomedia.CFG['HeadPhones']['music']
section = nzbtomedia.CFG.findsection('tv').isenabled()
print section