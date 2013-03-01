import logging
import logging.config
import os
import sys


def nzbtomedia_configure_logging(dirname):
  logFile = os.path.join(dirname, "postprocess.log")
  logging.config.fileConfig(os.path.join(dirname, "autoProcessMedia.cfg"))
  fileHandler = logging.FileHandler(logFile, encoding='utf-8', delay=True)
  fileHandler.formatter = logging.Formatter('%(asctime)s|%(levelname)-7.7s %(message)s', '%H:%M:%S')
  fileHandler.level = logging.DEBUG
  logging.getLogger().addHandler(fileHandler)


def create_destination(outputDestination):
    if not os.path.exists(outputDestination):
        try:
            Logger.info("CREATE DESTINATION: Creating destination folder: %s", outputDestination)
            os.makedirs(outputDestination)
        except Exception, e:
            Logger.error("CREATE DESTINATION: Not possible to create destination folder: %s. Exiting", e)
            sys.exit(-1)


def parse_other(args):
    return os.path.normpath(sys.argv[1]), '', '', ''


def parse_utorrent(args):
    # uTorrent usage: call TorrentToMedia.py "%D" "%N" "%L" "%I"
    inputDirectory = os.path.normpath(args[1])
    inputName = args[2]
    try:
        inputCategory = args[3]
    except:
        inputCategory = ''
    try:
        inputHash = args[4]
    except:
        inputHash = ''
        
    return inputDirectory, inputName, inputCategory, inputHash


def parse_deluge(args):
    # Deluge usage: call TorrentToMedia.py TORRENT_ID TORRENT_NAME TORRENT_DIR
    inputDirectory = os.path.normpath(sys.argv[3])
    inputName = sys.argv[2]
    inputCategory = '' # We dont have a category yet
    inputHash = ''
    return inputDirectory, inputName, inputCategory, inputHash


def parse_transmission(args):
    # Transmission usage: call TorrenToMedia.py (%TR_TORRENT_DIR% %TR_TORRENT_NAME% is passed on as environmental variables)
    inputDirectory = os.path.normpath(os.getenv('TR_TORRENT_DIR'))
    inputName = os.getenv('TR_TORRENT_NAME')
    inputCategory = '' # We dont have a category yet
    inputHash = ''
    return inputDirectory, inputName, inputCategory, inputHash


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
    return parseFunc(sys.argv)
