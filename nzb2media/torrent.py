from __future__ import annotations

import logging
import time

import nzb2media
import nzb2media.deluge
import nzb2media.qbittorrent
import nzb2media.synology
import nzb2media.transmission
import nzb2media.utorrent
from nzb2media.deluge import configure_deluge
from nzb2media.qbittorrent import configure_qbittorrent
from nzb2media.synology import configure_syno
from nzb2media.transmission import configure_transmission
from nzb2media.utorrent import configure_utorrent

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

CLIENTS = ['transmission', 'deluge', 'utorrent', 'rtorrent', 'qbittorrent', 'other', 'manual']
CLIENT_AGENT = None
CLASS = None
CHMOD_DIRECTORY = None
DEFAULT_DIRECTORY = None
RESUME = None
RESUME_ON_FAILURE = None

torrent_clients = {
    'deluge': nzb2media.deluge,
    'qbittorrent': nzb2media.qbittorrent,
    'transmission': nzb2media.transmission,
    'utorrent': nzb2media.utorrent,
    'synods': nzb2media.synology,
}


def configure_torrents(config):
    global CLIENT_AGENT
    global DEFAULT_DIRECTORY

    torrent_config = config['Torrent']
    CLIENT_AGENT = torrent_config['clientAgent']  # utorrent | deluge | transmission | rtorrent | vuze | qbittorrent | synods | other
    nzb2media.OUTPUT_DIRECTORY = torrent_config['outputDirectory']  # /abs/path/to/complete/
    DEFAULT_DIRECTORY = torrent_config['default_downloadDirectory']
    nzb2media.TORRENT_NO_MANUAL = int(torrent_config['no_manual'], 0)
    configure_torrent_linking(torrent_config)
    configure_flattening(torrent_config)
    configure_torrent_deletion(torrent_config)
    configure_torrent_categories(torrent_config)
    configure_torrent_permissions(torrent_config)
    configure_torrent_resuming(torrent_config)
    configure_utorrent(torrent_config)
    configure_transmission(torrent_config)
    configure_deluge(torrent_config)
    configure_qbittorrent(torrent_config)
    configure_syno(torrent_config)


def configure_torrent_linking(config):
    nzb2media.USE_LINK = config['useLink']  # no | hard | sym


def configure_flattening(config):
    global NO_FLATTEN
    NO_FLATTEN = config['noFlatten']
    if isinstance(NO_FLATTEN, str):
        NO_FLATTEN = NO_FLATTEN.split(',')


def configure_torrent_categories(config):
    nzb2media.CATEGORIES = config['categories']  # music,music_videos,pictures,software
    if isinstance(nzb2media.CATEGORIES, str):
        nzb2media.CATEGORIES = nzb2media.CATEGORIES.split(',')


def configure_torrent_resuming(config):
    global RESUME_ON_FAILURE
    global RESUME
    RESUME_ON_FAILURE = int(config['resumeOnFailure'])
    RESUME = int(config['resume'])


def configure_torrent_permissions(config):
    global CHMOD_DIRECTORY
    CHMOD_DIRECTORY = int(str(config['chmodDirectory']), 8)


def configure_torrent_deletion(config):
    nzb2media.DELETE_ORIGINAL = int(config['deleteOriginal'])


def configure_torrent_class():
    # create torrent class
    global CLASS
    CLASS = create_torrent_class(CLIENT_AGENT)


def create_torrent_class(client_agent) -> object | None:
    if nzb2media.APP_NAME != 'TorrentToMedia.py':
        return None  # Skip loading Torrent for NZBs.
    try:
        agent = torrent_clients[client_agent]
    except KeyError:
        return None
    else:
        nzb2media.deluge.configure_client()
        return agent.configure_client()


def pause_torrent(client_agent, input_hash, input_id, input_name):
    log.debug(f'Stopping torrent {input_name} in {client_agent} while processing')
    try:
        if client_agent == 'utorrent' and CLASS:
            CLASS.stop(input_hash)
        if client_agent == 'transmission' and CLASS:
            CLASS.stop_torrent(input_id)
        if client_agent == 'synods' and CLASS:
            CLASS.pause_task(input_id)
        if client_agent == 'deluge' and CLASS:
            CLASS.core.pause_torrent([input_id])
        if client_agent == 'qbittorrent' and CLASS:
            CLASS.pause(input_hash)
        time.sleep(5)
    except Exception:
        log.warning(f'Failed to stop torrent {input_name} in {client_agent}')


def resume_torrent(client_agent, input_hash, input_id, input_name):
    if RESUME != 1:
        return
    log.debug(f'Starting torrent {input_name} in {client_agent}')
    try:
        if client_agent == 'utorrent' and CLASS:
            CLASS.start(input_hash)
        if client_agent == 'transmission' and CLASS:
            CLASS.start_torrent(input_id)
        if client_agent == 'synods' and CLASS:
            CLASS.resume_task(input_id)
        if client_agent == 'deluge' and CLASS:
            CLASS.core.resume_torrent([input_id])
        if client_agent == 'qbittorrent' and CLASS:
            CLASS.resume(input_hash)
        time.sleep(5)
    except Exception:
        log.warning(f'Failed to start torrent {input_name} in {client_agent}')


def remove_torrent(client_agent, input_hash, input_id, input_name):
    if nzb2media.DELETE_ORIGINAL == 1 or nzb2media.USE_LINK == 'move':
        log.debug(f'Deleting torrent {input_name} from {client_agent}')
        try:
            if client_agent == 'utorrent' and CLASS:
                CLASS.removedata(input_hash)
                CLASS.remove(input_hash)
            if client_agent == 'transmission' and CLASS:
                CLASS.remove_torrent(input_id, True)
            if client_agent == 'synods' and CLASS:
                CLASS.delete_task(input_id)
            if client_agent == 'deluge' and CLASS:
                CLASS.core.remove_torrent(input_id, True)
            if client_agent == 'qbittorrent' and CLASS:
                CLASS.delete_permanently(input_hash)
            time.sleep(5)
        except Exception:
            log.warning(f'Failed to delete torrent {input_name} in {client_agent}')
    else:
        resume_torrent(client_agent, input_hash, input_id, input_name)


NO_FLATTEN: list[str] = []
