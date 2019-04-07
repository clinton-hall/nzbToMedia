# coding=utf-8
"""
A synchronous implementation of the Deluge RPC protocol.

Based on gevent-deluge by Christopher Rosell:
   https://github.com/chrippa/gevent-deluge

Example usage:

    from synchronousdeluge import DelgueClient

    client = DelugeClient()
    client.connect()

    # Wait for value
    download_location = client.core.get_config_value("download_location").get()
"""

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from .exceptions import DelugeRPCError


__title__ = 'synchronous-deluge'
__version__ = '0.1'
__author__ = 'Christian Dale'
