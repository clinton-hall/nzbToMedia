from __future__ import annotations

import time

import nzb2media
from nzb2media import logger

from .deluge import configure_client as deluge_client
from .qbittorrent import configure_client as qbittorrent_client
from .synology import configure_client as synology_client
from .transmission import configure_client as transmission_client
from .utorrent import configure_client as utorrent_client

torrent_clients = {
    'deluge': deluge_client,
    'qbittorrent': qbittorrent_client,
    'transmission': transmission_client,
    'utorrent': utorrent_client,
    'synods': synology_client,
}


def create_torrent_class(client_agent):
    if not nzb2media.APP_NAME == 'TorrentToMedia.py':
        return  # Skip loading Torrent for NZBs.

    client = torrent_clients.get(client_agent)
    if client:
        return client()


def pause_torrent(client_agent, input_hash, input_id, input_name):
    logger.debug(
        f'Stopping torrent {input_name} in {client_agent} while processing',
    )
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
        logger.warning(
            f'Failed to stop torrent {input_name} in {client_agent}',
        )


def resume_torrent(client_agent, input_hash, input_id, input_name):
    if not nzb2media.TORRENT_RESUME == 1:
        return
    logger.debug(f'Starting torrent {input_name} in {client_agent}')
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
        logger.warning(
            f'Failed to start torrent {input_name} in {client_agent}',
        )


def remove_torrent(client_agent, input_hash, input_id, input_name):
    if nzb2media.DELETE_ORIGINAL == 1 or nzb2media.USE_LINK == 'move':
        logger.debug(f'Deleting torrent {input_name} from {client_agent}')
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
            logger.warning(
                f'Failed to delete torrent {input_name} in {client_agent}',
            )
    else:
        resume_torrent(client_agent, input_hash, input_id, input_name)
