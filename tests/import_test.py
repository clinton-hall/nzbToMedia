def test_auto_process_imports():
    import nzb2media.auto_process
    assert nzb2media.auto_process

    import nzb2media.auto_process.books
    assert nzb2media.auto_process.books

    import nzb2media.auto_process.comics
    assert nzb2media.auto_process.comics

    import nzb2media.auto_process.common
    assert nzb2media.auto_process.common

    import nzb2media.auto_process.games
    assert nzb2media.auto_process.games

    import nzb2media.auto_process.movies
    assert nzb2media.auto_process.movies

    import nzb2media.auto_process.music
    assert nzb2media.auto_process.music

    import nzb2media.auto_process.tv
    assert nzb2media.auto_process.tv


def test_import_extractor():
    import nzb2media.extractor
    assert nzb2media.extractor


def test_import_managers():
    import nzb2media.managers
    assert nzb2media.managers

    import nzb2media.managers.pymedusa
    assert nzb2media.managers.pymedusa

    import nzb2media.managers.sickbeard
    assert nzb2media.managers.sickbeard


def test_import_nzb():
    import nzb2media.nzb
    assert nzb2media.nzb

    import nzb2media.nzb.configuration
    assert nzb2media.nzb.configuration


def test_import_plugins():
    import nzb2media.plugins
    assert nzb2media.plugins

    import nzb2media.plugins.plex
    assert nzb2media.plugins.plex

    import nzb2media.plugins.subtitles
    assert nzb2media.plugins.subtitles


def test_import_processor():
    import nzb2media.processor
    assert nzb2media.processor

    import nzb2media.processor.manual
    assert nzb2media.processor.manual

    import nzb2media.processor.nzb
    assert nzb2media.processor.nzb

    import nzb2media.processor.nzbget
    assert nzb2media.processor.nzbget

    import nzb2media.processor.sab
    assert nzb2media.processor.sab


def test_import_torrent():
    import nzb2media.torrent
    assert nzb2media.torrent

    import nzb2media.torrent.configuration
    assert nzb2media.torrent.configuration

    import nzb2media.torrent.deluge
    assert nzb2media.torrent.deluge

    import nzb2media.torrent.qbittorrent
    assert nzb2media.torrent.qbittorrent

    import nzb2media.torrent.synology
    assert nzb2media.torrent.synology

    import nzb2media.torrent.transmission
    assert nzb2media.torrent.transmission

    import nzb2media.torrent.utorrent
    assert nzb2media.torrent.utorrent


def test_import_utils():
    import nzb2media.utils
    assert nzb2media.utils

    import nzb2media.utils.common
    assert nzb2media.utils.common

    import nzb2media.utils.download_info
    assert nzb2media.utils.download_info

    import nzb2media.utils.encoding
    assert nzb2media.utils.encoding

    import nzb2media.utils.files
    assert nzb2media.utils.files

    import nzb2media.utils.identification
    assert nzb2media.utils.identification

    import nzb2media.utils.links
    assert nzb2media.utils.links

    import nzb2media.utils.naming
    assert nzb2media.utils.naming

    import nzb2media.utils.network
    assert nzb2media.utils.network

    import nzb2media.utils.nzb
    assert nzb2media.utils.nzb

    import nzb2media.utils.parsers
    assert nzb2media.utils.parsers

    import nzb2media.utils.paths
    assert nzb2media.utils.paths

    import nzb2media.utils.processes
    assert nzb2media.utils.processes

    import nzb2media.utils.torrent
    assert nzb2media.utils.torrent


def test_import_nzb2media():
    import nzb2media
    assert nzb2media

    import nzb2media.configuration
    assert nzb2media.configuration

    import nzb2media.databases
    assert nzb2media.databases

    import nzb2media.github_api
    assert nzb2media.github_api

    import nzb2media.main_db
    assert nzb2media.main_db

    import nzb2media.scene_exceptions
    assert nzb2media.scene_exceptions

    import nzb2media.transcoder
    assert nzb2media.transcoder

    import nzb2media.user_scripts
    assert nzb2media.user_scripts

    import nzb2media.version_check
    assert nzb2media.version_check
