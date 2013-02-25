import logging
import logging.config
import os.path
import sys

from utorrent.client import UTorrentClient

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
    # uTorrent usage: call TorrentToMedia.py "%D" "%N" "%L" "%I"
    inputDirectory = os.path.normpath(sys.argv[2])
    inputName = sys.argv[3]
    try:
        inputCategory = sys.argv[4]
    except:
        inputCategory = ''
    inputHash = sys.argv[5]
    if inputHash and useLink:
        utorrentClass = UTorrentClient(uTorrentWEBui, uTorrentUSR, uTorrentPWD)

def parse_deluge(args):
    # Deluge usage: call TorrentToMedia.py TORRENT_ID TORRENT_NAME TORRENT_DIR
    inputDirectory = os.path.normpath(sys.argv[3])
    inputName = sys.argv[2]
    inputCategory = '' # We dont have a category yet

def parse_transmission(args):
    # Transmission usage: call TorrenToMedia.py (%TR_TORRENT_DIR% %TR_TORRENT_NAME% is passed on as environmental variables)
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
