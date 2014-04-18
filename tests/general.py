import os
import sys
import nzbtomedia
import TorrentToMedia
from nzbtomedia.nzbToMediaUtil import find_download

os.environ['TR_TORRENT_DIR']="z:/downloads/complete/movie/The.Art.of.the.Steal.2013.LIMITED.1080p.BRRip.h264.AAC-RARBG"
os.environ['TR_TORRENT_NAME']="The.Art.of.the.Steal.2013.LIMITED.1080p.BRRip.h264.AAC-RARBG"
os.environ['TR_TORRENT_ID']="154206e6390a03bbf01e61f013e1a52494a52dfa"
os.environ['TR_TORRENT_HASH']="154206e6390a03bbf01e61f013e1a52494a52dfa"
#TorrentToMedia.main(sys.argv)

# Initialize the config
nzbtomedia.initialize()

clientAgent = nzbtomedia.NZB_CLIENTAGENT
nzbName = 'Anger.Management.S02E57.HDTV.x264-KILLERS'
#download_id = '51C9B415382894727C5C7D8442554D3AC08B390F'

download_id = 'SABnzbd_nzo_uBYaGb'
if find_download(clientAgent, nzbName, download_id):
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