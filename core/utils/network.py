import socket
import struct
import time

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
