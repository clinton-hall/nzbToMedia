from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

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

    logger.info('WakeOnLan sent for mac: {0}'.format(ethernet_address))


def test_connection(host, port):
    """Test network connection."""
    address = host, port
    try:
        socket.create_connection(address)
    except socket.error:
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
        logger.info('Attempt {0} of {1}'.format(attempt + 1, max_attempts, mac))
        if test_connection(host, port) == 'Up':
            logger.info('System with mac: {0} has been woken.'.format(mac))
            break
        wake_on_lan(mac)
        time.sleep(20)
    else:
        if test_connection(host, port) == 'Down':  # final check.
            msg = 'System with mac: {0} has not woken after {1} attempts.'
            logger.warning(msg.format(mac, max_attempts))

    logger.info('Continuing with the rest of the script.')


def server_responding(base_url):
    logger.debug('Attempting to connect to server at {0}'.format(base_url), 'SERVER')
    try:
        requests.get(base_url, timeout=(60, 120), verify=False)
    except (requests.ConnectionError, requests.exceptions.Timeout):
        logger.error('Server failed to respond at {0}'.format(base_url), 'SERVER')
        return False
    else:
        logger.debug('Server responded at {0}'.format(base_url), 'SERVER')
        return True


def find_download(client_agent, download_id):
    logger.debug('Searching for Download on {0} ...'.format(client_agent))
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
            base_url = '{0}:{1}/api'.format(core.SABNZBD_HOST, core.SABNZBD_PORT)
        else:
            base_url = 'http://{0}:{1}/api'.format(core.SABNZBD_HOST, core.SABNZBD_PORT)
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
