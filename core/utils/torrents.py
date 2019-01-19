import time

from qbittorrent import Client as qBittorrentClient
from synchronousdeluge.client import DelugeClient
from transmissionrpc.client import Client as TransmissionClient
from utorrent.client import UTorrentClient

import core
from core import logger


def create_torrent_class(client_agent):
    # Hardlink solution for Torrents
    tc = None

    if client_agent == 'utorrent':
        try:
            logger.debug('Connecting to {0}: {1}'.format(client_agent, core.UTORRENT_WEB_UI))
            tc = UTorrentClient(core.UTORRENT_WEB_UI, core.UTORRENT_USER, core.UTORRENT_PASSWORD)
        except Exception:
            logger.error('Failed to connect to uTorrent')

    if client_agent == 'transmission':
        try:
            logger.debug('Connecting to {0}: http://{1}:{2}'.format(
                client_agent, core.TRANSMISSION_HOST, core.TRANSMISSION_PORT))
            tc = TransmissionClient(core.TRANSMISSION_HOST, core.TRANSMISSION_PORT,
                                    core.TRANSMISSIONUSR,
                                    core.TRANSMISSIONPWD)
        except Exception:
            logger.error('Failed to connect to Transmission')

    if client_agent == 'deluge':
        try:
            logger.debug('Connecting to {0}: http://{1}:{2}'.format(client_agent, core.DELUGEHOST, core.DELUGEPORT))
            tc = DelugeClient()
            tc.connect(host=core.DELUGEHOST, port=core.DELUGEPORT, username=core.DELUGEUSR,
                       password=core.DELUGEPWD)
        except Exception:
            logger.error('Failed to connect to Deluge')

    if client_agent == 'qbittorrent':
        try:
            logger.debug('Connecting to {0}: http://{1}:{2}'.format(client_agent, core.QBITTORRENTHOST, core.QBITTORRENTPORT))
            tc = qBittorrentClient('http://{0}:{1}/'.format(core.QBITTORRENTHOST, core.QBITTORRENTPORT))
            tc.login(core.QBITTORRENTUSR, core.QBITTORRENTPWD)
        except Exception:
            logger.error('Failed to connect to qBittorrent')

    return tc


def pause_torrent(client_agent, input_hash, input_id, input_name):
    logger.debug('Stopping torrent {0} in {1} while processing'.format(input_name, client_agent))
    try:
        if client_agent == 'utorrent' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.stop(input_hash)
        if client_agent == 'transmission' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.stop_torrent(input_id)
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
        if client_agent == 'deluge' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.core.resume_torrent([input_id])
        if client_agent == 'qbittorrent' and core.TORRENT_CLASS != '':
            core.TORRENT_CLASS.resume(input_hash)
        time.sleep(5)
    except Exception:
        logger.warning('Failed to start torrent {0} in {1}'.format(input_name, client_agent))


def remove_torrent(client_agent, input_hash, input_id, input_name):
    if core.DELETE_ORIGINAL == 1 or core.USELINK == 'move':
        logger.debug('Deleting torrent {0} from {1}'.format(input_name, client_agent))
        try:
            if client_agent == 'utorrent' and core.TORRENT_CLASS != '':
                core.TORRENT_CLASS.removedata(input_hash)
                core.TORRENT_CLASS.remove(input_hash)
            if client_agent == 'transmission' and core.TORRENT_CLASS != '':
                core.TORRENT_CLASS.remove_torrent(input_id, True)
            if client_agent == 'deluge' and core.TORRENT_CLASS != '':
                core.TORRENT_CLASS.core.remove_torrent(input_id, True)
            if client_agent == 'qbittorrent' and core.TORRENT_CLASS != '':
                core.TORRENT_CLASS.delete_permanently(input_hash)
            time.sleep(5)
        except Exception:
            logger.warning('Failed to delete torrent {0} in {1}'.format(input_name, client_agent))
    else:
        resume_torrent(client_agent, input_hash, input_id, input_name)
