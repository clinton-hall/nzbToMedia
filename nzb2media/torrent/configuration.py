from __future__ import annotations

import nzb2media
from nzb2media.utils.torrent import create_torrent_class


def configure_torrents(config):
    torrent_config = config['Torrent']
    nzb2media.TORRENT_CLIENT_AGENT = torrent_config['clientAgent']  # utorrent | deluge | transmission | rtorrent | vuze | qbittorrent | synods | other
    nzb2media.OUTPUT_DIRECTORY = torrent_config['outputDirectory']  # /abs/path/to/complete/
    nzb2media.TORRENT_DEFAULT_DIRECTORY = torrent_config['default_downloadDirectory']
    nzb2media.TORRENT_NO_MANUAL = int(torrent_config['no_manual'], 0)
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
    nzb2media.USE_LINK = config['useLink']  # no | hard | sym


def configure_flattening(config):
    nzb2media.NOFLATTEN = config['noFlatten']
    if isinstance(nzb2media.NOFLATTEN, str):
        nzb2media.NOFLATTEN = nzb2media.NOFLATTEN.split(',')


def configure_torrent_categories(config):
    nzb2media.CATEGORIES = config['categories']  # music,music_videos,pictures,software
    if isinstance(nzb2media.CATEGORIES, str):
        nzb2media.CATEGORIES = nzb2media.CATEGORIES.split(',')


def configure_torrent_resuming(config):
    nzb2media.TORRENT_RESUME_ON_FAILURE = int(config['resumeOnFailure'])
    nzb2media.TORRENT_RESUME = int(config['resume'])


def configure_torrent_permissions(config):
    nzb2media.TORRENT_CHMOD_DIRECTORY = int(str(config['chmodDirectory']), 8)


def configure_torrent_deletion(config):
    nzb2media.DELETE_ORIGINAL = int(config['deleteOriginal'])


def configure_utorrent(config):
    nzb2media.UTORRENT_WEB_UI = config['uTorrentWEBui']  # http://localhost:8090/gui/
    nzb2media.UTORRENT_USER = config['uTorrentUSR']  # mysecretusr
    nzb2media.UTORRENT_PASSWORD = config['uTorrentPWD']  # mysecretpwr


def configure_transmission(config):
    nzb2media.TRANSMISSION_HOST = config['TransmissionHost']  # localhost
    nzb2media.TRANSMISSION_PORT = int(config['TransmissionPort'])
    nzb2media.TRANSMISSION_USER = config['TransmissionUSR']  # mysecretusr
    nzb2media.TRANSMISSION_PASSWORD = config['TransmissionPWD']  # mysecretpwr


def configure_syno(config):
    nzb2media.SYNO_HOST = config['synoHost']  # localhost
    nzb2media.SYNO_PORT = int(config['synoPort'])
    nzb2media.SYNO_USER = config['synoUSR']  # mysecretusr
    nzb2media.SYNO_PASSWORD = config['synoPWD']  # mysecretpwr


def configure_deluge(config):
    nzb2media.DELUGE_HOST = config['DelugeHost']  # localhost
    nzb2media.DELUGE_PORT = int(config['DelugePort'])  # 8084
    nzb2media.DELUGE_USER = config['DelugeUSR']  # mysecretusr
    nzb2media.DELUGE_PASSWORD = config['DelugePWD']  # mysecretpwr


def configure_qbittorrent(config):
    nzb2media.QBITTORRENT_HOST = config['qBittorrentHost']  # localhost
    nzb2media.QBITTORRENT_PORT = int(config['qBittorrentPort'])  # 8080
    nzb2media.QBITTORRENT_USER = config['qBittorrentUSR']  # mysecretusr
    nzb2media.QBITTORRENT_PASSWORD = config['qBittorrentPWD']  # mysecretpwr


def configure_torrent_class():
    # create torrent class
    nzb2media.TORRENT_CLASS = create_torrent_class(nzb2media.TORRENT_CLIENT_AGENT)
