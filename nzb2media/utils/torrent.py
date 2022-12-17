from __future__ import annotations

import logging
import time

import nzb2media
from nzb2media.torrent import deluge
from nzb2media.torrent import qbittorrent
from nzb2media.torrent import synology
from nzb2media.torrent import transmission
from nzb2media.torrent import utorrent

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

torrent_clients = {
    'deluge': deluge,
    'qbittorrent': qbittorrent,
    'transmission': transmission,
    'utorrent': utorrent,
    'synods': synology,
}


def create_torrent_class(client_agent):
    if not nzb2media.APP_NAME == 'TorrentToMedia.py':
        return  # Skip loading Torrent for NZBs.

    try:
        agent = torrent_clients[client_agent]
    except KeyError:
        return
    else:
        return agent.configure_client()


def pause_torrent(client_agent, input_hash, input_id, input_name):
    log.debug(f'Stopping torrent {input_name} in {client_agent} while processing')
    try:
        if client_agent == 'utorrent' and nzb2media.TORRENT_CLASS != '':
            nzb2media.TORRENT_CLASS.stop(input_hash)
        if client_agent == 'transmission' and nzb2media.TORRENT_CLASS != '':
            nzb2media.TORRENT_CLASS.stop_torrent(input_id)
        if client_agent == 'synods' and nzb2media.TORRENT_CLASS != '':
            nzb2media.TORRENT_CLASS.pause_task(input_id)
        if client_agent == 'deluge' and nzb2media.TORRENT_CLASS != '':
            nzb2media.TORRENT_CLASS.core.pause_torrent([input_id])
        if client_agent == 'qbittorrent' and nzb2media.TORRENT_CLASS != '':
            nzb2media.TORRENT_CLASS.pause(input_hash)
        time.sleep(5)
    except Exception:
        log.warning(f'Failed to stop torrent {input_name} in {client_agent}')


def resume_torrent(client_agent, input_hash, input_id, input_name):
    if not nzb2media.TORRENT_RESUME == 1:
        return
    log.debug(f'Starting torrent {input_name} in {client_agent}')
    try:
        if client_agent == 'utorrent' and nzb2media.TORRENT_CLASS != '':
            nzb2media.TORRENT_CLASS.start(input_hash)
        if client_agent == 'transmission' and nzb2media.TORRENT_CLASS != '':
            nzb2media.TORRENT_CLASS.start_torrent(input_id)
        if client_agent == 'synods' and nzb2media.TORRENT_CLASS != '':
            nzb2media.TORRENT_CLASS.resume_task(input_id)
        if client_agent == 'deluge' and nzb2media.TORRENT_CLASS != '':
            nzb2media.TORRENT_CLASS.core.resume_torrent([input_id])
        if client_agent == 'qbittorrent' and nzb2media.TORRENT_CLASS != '':
            nzb2media.TORRENT_CLASS.resume(input_hash)
        time.sleep(5)
    except Exception:
        log.warning(f'Failed to start torrent {input_name} in {client_agent}')


def remove_torrent(client_agent, input_hash, input_id, input_name):
    if nzb2media.DELETE_ORIGINAL == 1 or nzb2media.USE_LINK == 'move':
        log.debug(f'Deleting torrent {input_name} from {client_agent}')
        try:
            if client_agent == 'utorrent' and nzb2media.TORRENT_CLASS != '':
                nzb2media.TORRENT_CLASS.removedata(input_hash)
                nzb2media.TORRENT_CLASS.remove(input_hash)
            if client_agent == 'transmission' and nzb2media.TORRENT_CLASS != '':
                nzb2media.TORRENT_CLASS.remove_torrent(input_id, True)
            if client_agent == 'synods' and nzb2media.TORRENT_CLASS != '':
                nzb2media.TORRENT_CLASS.delete_task(input_id)
            if client_agent == 'deluge' and nzb2media.TORRENT_CLASS != '':
                nzb2media.TORRENT_CLASS.core.remove_torrent(input_id, True)
            if client_agent == 'qbittorrent' and nzb2media.TORRENT_CLASS != '':
                nzb2media.TORRENT_CLASS.delete_permanently(input_hash)
            time.sleep(5)
        except Exception:
            log.warning(f'Failed to delete torrent {input_name} in {client_agent}')
    else:
        resume_torrent(client_agent, input_hash, input_id, input_name)
