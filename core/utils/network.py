import socket
import struct
import time

import core
from core import logger


# Wake function
def wake_on_lan(ethernet_address):
    addr_byte = ethernet_address.split(':')
    hw_addr = struct.pack(b'BBBBBB', int(addr_byte[0], 16),
                          int(addr_byte[1], 16),
                          int(addr_byte[2], 16),
                          int(addr_byte[3], 16),
                          int(addr_byte[4], 16),
                          int(addr_byte[5], 16))

    # Build the Wake-On-LAN 'Magic Packet'...

    msg = b'\xff' * 6 + hw_addr * 16

    # ...and send it to the broadcast address using UDP

    ss = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ss.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    ss.sendto(msg, ('<broadcast>', 9))
    ss.close()


# Test Connection function
def test_connection(host, port):
    try:
        socket.create_connection((host, port))
        return 'Up'
    except Exception:
        return 'Down'


def wake_up():
    host = core.CFG['WakeOnLan']['host']
    port = int(core.CFG['WakeOnLan']['port'])
    mac = core.CFG['WakeOnLan']['mac']

    i = 1
    while test_connection(host, port) == 'Down' and i < 4:
        logger.info(('Sending WakeOnLan Magic Packet for mac: {0}'.format(mac)))
        wake_on_lan(mac)
        time.sleep(20)
        i = i + 1

    if test_connection(host, port) == 'Down':  # final check.
        logger.warning('System with mac: {0} has not woken after 3 attempts. '
                       'Continuing with the rest of the script.'.format(mac))
    else:
        logger.info('System with mac: {0} has been woken. Continuing with the rest of the script.'.format(mac))
