import os
import sys
import TorrentToMedia
import nzbtomedia
from nzbtomedia.Transcoder import Transcoder
from nzbtomedia.nzbToMediaUtil import listMediaFiles

os.environ['TR_TORRENT_DIR']="z:/downloads/complete/movie/The.Lego.Movie.2014.R5.x264.English.XviD-vTg.nfo_0166_-_The.Lego.Movie.2014.R5.x264.English.XviD-vTg.nfo_yEn.cp(tt1490017)"
os.environ['TR_TORRENT_NAME']="The.Lego.Movie.2014.R5.x264.English.XviD-vTg.nfo_0166_-_The.Lego.Movie.2014.R5.x264.English.XviD-vTg.nfo_yEn.cp(tt1490017)"
os.environ['TR_TORRENT_ID']="7855bb5c20189a73ea45aaf80c2541dfcf897f9d"
os.environ['TR_TORRENT_HASH']="7855bb5c20189a73ea45aaf80c2541dfcf897f9d"

# Initialize the config
nzbtomedia.initialize()

for video in listMediaFiles('Y:\Movies\Jobs (2013)'):
    if nzbtomedia.TRANSCODE and Transcoder().isVideoGood(video):
        print 'Good'
    else:
        print 'Bad'
