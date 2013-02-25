import logging
import logging.config
import os.path
import sys


def nzbtomedia_configure_logging(dirname):
  logFile = os.path.join(dirname, "postprocess.log")
  logging.config.fileConfig(os.path.join(dirname, "autoProcessMedia.cfg"))
  fileHandler = logging.FileHandler(logFile, encoding='utf-8', delay=True)
  fileHandler.formatter = logging.Formatter('%(asctime)s|%(levelname)-7.7s %(message)s', '%H:%M:%S')
  fileHandler.level = logging.DEBUG
  logging.getLogger().addHandler(fileHandler)


def parse_other(args):
        return os.path.normpath(sys.argv[1]), '', ''


def parse_utorrent(args):
        # We will pass in 'utorrent' '%D', '%N', and '%L' (if it exists), from uTorrent
        # In short pass "/path/to/downloaded/torrent/ name" to TorrentToMedia.py, eg  >>>> TorrentToMedia.py /Downloaded/MovieName.2013.BluRay.1080p.x264-10bit.DTS MovieName.2013.BluRay.1080p.x264-10bit.DTS <<<<
        inputDirectory = os.path.normpath(sys.argv[2])
        inputName = sys.argv[3]
        try: #assume we have a label.
                inputCategory = sys.argv[4] # We dont have a category yet
        except:
                inputCategory = '' # We dont have a category yet


def parse_deluge(args):
        # We will assume this to be the passin from deluge. torrent id, torrent name, torrent save path.
        inputDirectory = os.path.normpath(sys.argv[3])
        inputName = sys.argv[2]
        inputCategory = '' # We dont have a category yet


def parse_transmission(args):
        # We will pass in %TR_TORRENT_DIR% %TR_TORRENT_NAME% from Transmission
        # In short pass "/path/to/downloaded/torrent/ name" to TorrentToMedia.py, eg  >>>> TorrentToMedia.py /Downloaded/MovieName.2013.BluRay.1080p.x264-10bit.DTS MovieName.2013.BluRay.1080p.x264-10bit.DTS <<<<
        inputDirectory = os.path.normpath(os.getenv('TR_TORRENT_DIR'))
        inputName = os.getenv('TR_TORRENT_NAME')
        inputCategory = '' # We dont have a category yet


__ARG_PARSERS__ = {
        'other': parse_other,
        'utorrent': parse_utorrent,
        'deluge': parse_deluge,
        'transmission': parse_transmission,
}


def parse_args(clientAgent):
        parseFunc = __ARG_PARSERS__.get(clientAgent, None)
        if not parseFunc:
                raise RuntimeError("Could not find client-agent")
        parseFunc(sys.argv)
