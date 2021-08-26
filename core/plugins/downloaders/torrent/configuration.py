from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import core
from core.plugins.downloaders.torrent.utils import create_torrent_class


def configure_torrents(config):
    torrent_config = config['Torrent']
    core.TORRENT_CLIENT_AGENT = torrent_config['clientAgent']  # utorrent | deluge | transmission | rtorrent | vuze | qbittorrent | synods | other
    core.OUTPUT_DIRECTORY = torrent_config['outputDirectory']  # /abs/path/to/complete/
    core.TORRENT_DEFAULT_DIRECTORY = torrent_config['default_downloadDirectory']
    core.TORRENT_NO_MANUAL = int(torrent_config['no_manual'], 0)

    configure_torrent_linking(torrent_config)
    configure_flattening(torrent_config)
    configure_torrent_deletion(torrent_config)
    configure_torrent_categories(torrent_config)
    configure_torrent_permissions(torrent_config)
    configure_torrent_resuming(torrent_config)
    configure_utorrent(torrent_config)
    configure_transmission(torrent_config)
    configure_deluge(torrent_config)
    configure_qbittorrent(torrent_config)
    configure_syno(torrent_config)


def configure_torrent_linking(config):
    core.USE_LINK = config['useLink']  # no | hard | sym


def configure_flattening(config):
    core.NOFLATTEN = (config['noFlatten'])
    if isinstance(core.NOFLATTEN, str):
        core.NOFLATTEN = core.NOFLATTEN.split(',')


def configure_torrent_categories(config):
    core.CATEGORIES = (config['categories'])  # music,music_videos,pictures,software
    if isinstance(core.CATEGORIES, str):
        core.CATEGORIES = core.CATEGORIES.split(',')


def configure_torrent_resuming(config):
    core.TORRENT_RESUME_ON_FAILURE = int(config['resumeOnFailure'])
    core.TORRENT_RESUME = int(config['resume'])


def configure_torrent_permissions(config):
    core.TORRENT_CHMOD_DIRECTORY = int(str(config['chmodDirectory']), 8)


def configure_torrent_deletion(config):
    core.DELETE_ORIGINAL = int(config['deleteOriginal'])


def configure_utorrent(config):
    core.UTORRENT_WEB_UI = config['uTorrentWEBui']  # http://localhost:8090/gui/
    core.UTORRENT_USER = config['uTorrentUSR']  # mysecretusr
    core.UTORRENT_PASSWORD = config['uTorrentPWD']  # mysecretpwr


def configure_transmission(config):
    core.TRANSMISSION_HOST = config['TransmissionHost']  # localhost
    core.TRANSMISSION_PORT = int(config['TransmissionPort'])
    core.TRANSMISSION_USER = config['TransmissionUSR']  # mysecretusr
    core.TRANSMISSION_PASSWORD = config['TransmissionPWD']  # mysecretpwr


def configure_syno(config):
    core.SYNO_HOST = config['synoHost']  # localhost
    core.SYNO_PORT = int(config['synoPort'])
    core.SYNO_USER = config['synoUSR']  # mysecretusr
    core.SYNO_PASSWORD = config['synoPWD']  # mysecretpwr


def configure_deluge(config):
    core.DELUGE_HOST = config['DelugeHost']  # localhost
    core.DELUGE_PORT = int(config['DelugePort'])  # 8084
    core.DELUGE_USER = config['DelugeUSR']  # mysecretusr
    core.DELUGE_PASSWORD = config['DelugePWD']  # mysecretpwr


def configure_qbittorrent(config):
    core.QBITTORRENT_HOST = config['qBittorrentHost']  # localhost
    core.QBITTORRENT_PORT = int(config['qBittorrentPort'])  # 8080
    core.QBITTORRENT_USER = config['qBittorrentUSR']  # mysecretusr
    core.QBITTORRENT_PASSWORD = config['qBittorrentPWD']  # mysecretpwr


def configure_torrent_class():
    # create torrent class
    core.TORRENT_CLASS = create_torrent_class(core.TORRENT_CLIENT_AGENT)
