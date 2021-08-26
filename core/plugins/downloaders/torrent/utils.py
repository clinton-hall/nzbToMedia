from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import time

import core
from core import logger

from .deluge import configure_client as deluge_client
from .qbittorrent import configure_client as qbittorrent_client
from .transmission import configure_client as transmission_client
from .utorrent import configure_client as utorrent_client
from .synology import configure_client as synology_client

torrent_clients = {
    'deluge': deluge_client,
    'qbittorrent': qbittorrent_client,
    'transmission': transmission_client,
    'utorrent': utorrent_client,
    'synods': synology_client,
}


def create_torrent_class(client_agent):
    if not core.APP_NAME == 'TorrentToMedia.py':
        return  # Skip loading Torrent for NZBs.

    client = torrent_clients.get(client_agent)
    if client:
        return client()


def pause_torrent(client_agent, input_hash, input_id, input_name):
    logger.debug('Stopping torrent {0} in {1} while processing'.format(input_name, client_agent))
    try:
        if client_agent == 'utorrent' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.stop(input_hash)
        if client_agent == 'transmission' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.stop_torrent(input_id)
        if client_agent == 'synods' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.pause_task(input_id)
        if client_agent == 'deluge' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.core.pause_torrent([input_id])
        if client_agent == 'qbittorrent' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.pause(input_hash)
        time.sleep(5)
    except Exception:
        logger.warning('Failed to stop torrent {0} in {1}'.format(input_name, client_agent))


def resume_torrent(client_agent, input_hash, input_id, input_name):
    if not core.TORRENT_RESUME == 1:
        return
    logger.debug('Starting torrent {0} in {1}'.format(input_name, client_agent))
    try:
        if client_agent == 'utorrent' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.start(input_hash)
        if client_agent == 'transmission' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.start_torrent(input_id)
        if client_agent == 'synods' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.resume_task(input_id)
        if client_agent == 'deluge' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.core.resume_torrent([input_id])
        if client_agent == 'qbittorrent' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.resume(input_hash)
        time.sleep(5)
    except Exception:
        logger.warning('Failed to start torrent {0} in {1}'.format(input_name, client_agent))


def remove_torrent(client_agent, input_hash, input_id, input_name):
    if core.DELETE_ORIGINAL == 1 or core.USE_LINK == 'move':
        logger.debug('Deleting torrent {0} from {1}'.format(input_name, client_agent))
        try:
            if client_agent == 'utorrent' and core.TORRENT_CLASS != '':
                core.TORRENT_CLASS.removedata(input_hash)
                core.TORRENT_CLASS.remove(input_hash)
            if client_agent == 'transmission' and core.TORRENT_CLASS != '':
                core.TORRENT_CLASS.remove_torrent(input_id, True)
            if client_agent == 'synods' and core.TORRENT_CLASS != '':
                core.TORRENT_CLASS.delete_task(input_id)
            if client_agent == 'deluge' and core.TORRENT_CLASS != '':
                core.TORRENT_CLASS.core.remove_torrent(input_id, True)
            if client_agent == 'qbittorrent' and core.TORRENT_CLASS != '':
                core.TORRENT_CLASS.delete_permanently(input_hash)
            time.sleep(5)
        except Exception:
            logger.warning('Failed to delete torrent {0} in {1}'.format(input_name, client_agent))
    else:
        resume_torrent(client_agent, input_hash, input_id, input_name)
