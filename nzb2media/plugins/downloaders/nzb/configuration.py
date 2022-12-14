from __future__ import annotations

import nzb2media


def configure_nzbs(config):
    nzb_config = config['Nzb']
    nzb2media.NZB_CLIENT_AGENT = nzb_config['clientAgent']  # sabnzbd
    nzb2media.NZB_DEFAULT_DIRECTORY = nzb_config['default_downloadDirectory']
    nzb2media.NZB_NO_MANUAL = int(nzb_config['no_manual'], 0)

    configure_sabnzbd(nzb_config)


def configure_sabnzbd(config):
    nzb2media.SABNZBD_HOST = config['sabnzbd_host']
    nzb2media.SABNZBD_PORT = int(
        config['sabnzbd_port'] or 8080,
    )  # defaults to accommodate NzbGet
    nzb2media.SABNZBD_APIKEY = config['sabnzbd_apikey']
