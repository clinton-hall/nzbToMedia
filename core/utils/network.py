from __future__ import annotations

import socket
import struct
import time

import requests

import core
from core import logger


def make_wake_on_lan_packet(mac_address):
    """Build the Wake-On-LAN 'Magic Packet'."""
    address = (
        int(value, 16)
        for value in mac_address.split(':')
    )
    fmt = 'BBBBBB'
    hardware_address = struct.pack(fmt, *address)
    broadcast_address = b'\xFF' * 6  # FF:FF:FF:FF:FF:FF
    return broadcast_address + hardware_address * 16


def wake_on_lan(ethernet_address):
    """Send a WakeOnLan request."""
    # Create the WoL magic packet
    magic_packet = make_wake_on_lan_packet(ethernet_address)

    # ...and send it to the broadcast address using UDP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        connection.sendto(magic_packet, ('<broadcast>', 9))

    logger.info(f'WakeOnLan sent for mac: {ethernet_address}')


def test_connection(host, port):
    """Test network connection."""
    address = host, port
    try:
        socket.create_connection(address)
    except OSError:
        return 'Down'
    else:
        return 'Up'


def wake_up():
    wol = core.CFG['WakeOnLan']
    host = wol['host']
    port = int(wol['port'])
    mac = wol['mac']
    max_attempts = 4

    logger.info('Trying to wake On lan.')

    for attempt in range(0, max_attempts):
        logger.info(f'Attempt {attempt + 1} of {max_attempts}')
        if test_connection(host, port) == 'Up':
            logger.info(f'System with mac: {mac} has been woken.')
            break
        wake_on_lan(mac)
        time.sleep(20)
    else:
        if test_connection(host, port) == 'Down':  # final check.
            msg = 'System with mac: {0} has not woken after {1} attempts.'
            logger.warning(msg.format(mac, max_attempts))

    logger.info('Continuing with the rest of the script.')


def server_responding(base_url):
    logger.debug(f'Attempting to connect to server at {base_url}', 'SERVER')
    try:
        requests.get(base_url, timeout=(60, 120), verify=False)
    except (requests.ConnectionError, requests.exceptions.Timeout):
        logger.error(f'Server failed to respond at {base_url}', 'SERVER')
        return False
    else:
        logger.debug(f'Server responded at {base_url}', 'SERVER')
        return True


def find_download(client_agent, download_id):
    logger.debug(f'Searching for Download on {client_agent} ...')
    if client_agent == 'utorrent':
        torrents = core.TORRENT_CLASS.list()[1]['torrents']
        for torrent in torrents:
            if download_id in torrent:
                return True
    if client_agent == 'transmission':
        torrents = core.TORRENT_CLASS.get_torrents()
        for torrent in torrents:
            torrent_hash = torrent.hashString
            if torrent_hash == download_id:
                return True
    if client_agent == 'deluge':
        return False
    if client_agent == 'qbittorrent':
        torrents = core.TORRENT_CLASS.torrents()
        for torrent in torrents:
            if torrent['hash'] == download_id:
                return True
    if client_agent == 'sabnzbd':
        if 'http' in core.SABNZBD_HOST:
            base_url = f'{core.SABNZBD_HOST}:{core.SABNZBD_PORT}/api'
        else:
            base_url = f'http://{core.SABNZBD_HOST}:{core.SABNZBD_PORT}/api'
        url = base_url
        params = {
            'apikey': core.SABNZBD_APIKEY,
            'mode': 'get_files',
            'output': 'json',
            'value': download_id,
        }
        try:
            r = requests.get(url, params=params, verify=False, timeout=(30, 120))
        except requests.ConnectionError:
            logger.error('Unable to open URL')
            return False  # failure

        result = r.json()
        if result['files']:
            return True
    return False
