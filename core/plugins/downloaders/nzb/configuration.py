from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import core


def configure_nzbs(config):
    nzb_config = config['Nzb']
    core.NZB_CLIENT_AGENT = nzb_config['clientAgent']  # sabnzbd
    core.NZB_DEFAULT_DIRECTORY = nzb_config['default_downloadDirectory']

    configure_sabnzbd(nzb_config)


def configure_sabnzbd(config):
    core.SABNZBD_HOST = config['sabnzbd_host']
    core.SABNZBD_PORT = int(config['sabnzbd_port'] or 8080)  # defaults to accommodate NzbGet
    core.SABNZBD_APIKEY = config['sabnzbd_apikey']
