import os
import sys
import nzbtomedia
import TorrentToMedia
from nzbtomedia.nzbToMediaUtil import find_download, clean_nzbname, listMediaFiles

nzbtomedia.initialize()

download_id = 'SABnzbd_nzo_qhoQ7m'
if find_download('sabnzbd', download_id):
    print 'found'
else:
    print 'no luck'

print nzbtomedia.CFG['SickBear','NzbDrone']['tv'].isenabled()
print nzbtomedia.CFG['SickBeard','NzbDrone']['tv'].isenabled()

if nzbtomedia.CFG['SickBeard', 'NzbDrone', 'CouchPotato']['tv']:
    print True
else:
    print False

if nzbtomedia.CFG['SickBeard']['tv']:
    print True
else:
    print False

print
print nzbtomedia.SUBSECTIONS["SickBeard"]
print
print nzbtomedia.CFG.findsection('tv')
print
print nzbtomedia.CFG.sections
print
sections = ("CouchPotato", "SickBeard", "NzbDrone", "HeadPhones", "Mylar", "Gamez")
print nzbtomedia.CFG[sections].sections
print nzbtomedia.CFG['SickBeard'].sections
print
print nzbtomedia.CFG['SickBeard','NzbDrone']
print nzbtomedia.CFG['SickBeard']