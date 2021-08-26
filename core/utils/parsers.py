from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os

import core
from core import logger


def parse_other(args):
    return os.path.normpath(args[1]), '', '', '', ''


def parse_rtorrent(args):
    # rtorrent usage: system.method.set_key = event.download.finished,TorrentToMedia,
    # 'execute={/path/to/nzbToMedia/TorrentToMedia.py,\'$d.get_base_path=\',\'$d.get_name=\',\'$d.get_custom1=\',\'$d.get_hash=\'}'
    input_directory = os.path.normpath(args[1])
    try:
        input_name = args[2]
    except Exception:
        input_name = ''
    try:
        input_category = args[3]
    except Exception:
        input_category = ''
    try:
        input_hash = args[4]
    except Exception:
        input_hash = ''
    try:
        input_id = args[4]
    except Exception:
        input_id = ''

    return input_directory, input_name, input_category, input_hash, input_id


def parse_utorrent(args):
    # uTorrent usage: call TorrentToMedia.py '%D' '%N' '%L' '%I'
    input_directory = os.path.normpath(args[1])
    input_name = args[2]
    try:
        input_category = args[3]
    except Exception:
        input_category = ''
    try:
        input_hash = args[4]
    except Exception:
        input_hash = ''
    try:
        input_id = args[4]
    except Exception:
        input_id = ''

    return input_directory, input_name, input_category, input_hash, input_id


def parse_deluge(args):
    # Deluge usage: call TorrentToMedia.py TORRENT_ID TORRENT_NAME TORRENT_DIR
    input_directory = os.path.normpath(args[3])
    input_name = args[2]
    input_hash = args[1]
    input_id = args[1]
    try:
        input_category = core.TORRENT_CLASS.core.get_torrent_status(input_id, ['label']).get(b'label').decode()
    except Exception:
        input_category = ''
    return input_directory, input_name, input_category, input_hash, input_id


def parse_transmission(args):
    # Transmission usage: call TorrenToMedia.py (%TR_TORRENT_DIR% %TR_TORRENT_NAME% is passed on as environmental variables)
    input_directory = os.path.normpath(os.getenv('TR_TORRENT_DIR'))
    input_name = os.getenv('TR_TORRENT_NAME')
    input_category = ''  # We dont have a category yet
    input_hash = os.getenv('TR_TORRENT_HASH')
    input_id = os.getenv('TR_TORRENT_ID')
    return input_directory, input_name, input_category, input_hash, input_id


def parse_synods(args):
    # Synology/Transmission usage: call TorrenToMedia.py (%TR_TORRENT_DIR% %TR_TORRENT_NAME% is passed on as environmental variables)
    input_directory = ''
    input_id = ''
    input_category = ''
    input_name = os.getenv('TR_TORRENT_NAME')
    input_hash = os.getenv('TR_TORRENT_HASH')
    if not input_name: # No info passed. Assume manual download.
        return input_directory, input_name, input_category, input_hash, input_id
    input_id = 'dbid_{0}'.format(os.getenv('TR_TORRENT_ID'))
    #res = core.TORRENT_CLASS.tasks_list(additional_param='detail')
    res = core.TORRENT_CLASS.tasks_info(input_id, additional_param='detail')
    logger.debug('result from syno {0}'.format(res))
    if res['success']:
        try:
            tasks = res['data']['tasks']
            task = [ task for task in tasks if task['id'] == input_id ][0]
            input_id = task['id']
            input_directory = task['additional']['detail']['destination']
        except:
            logger.error('unable to find download details in Synology DS')
        #Syno paths appear to be relative. Let's test to see if the returned path exists, and if not append to /volume1/
        if not os.path.isdir(input_directory):
            for root in ['/volume1/', '/volume2/', '/volume3/', '/volume4/']:
                if os.path.isdir(os.path.join(root, input_directory)):
                    input_directory = os.path.join(root, input_directory)
                    break
    return input_directory, input_name, input_category, input_hash, input_id


def parse_vuze(args):
    # vuze usage: C:\full\path\to\nzbToMedia\TorrentToMedia.py '%D%N%L%I%K%F'
    try:
        cur_input = args[1].split(',')
    except Exception:
        cur_input = []
    try:
        input_directory = os.path.normpath(cur_input[0])
    except Exception:
        input_directory = ''
    try:
        input_name = cur_input[1]
    except Exception:
        input_name = ''
    try:
        input_category = cur_input[2]
    except Exception:
        input_category = ''
    try:
        input_hash = cur_input[3]
    except Exception:
        input_hash = ''
    try:
        input_id = cur_input[3]
    except Exception:
        input_id = ''
    try:
        if cur_input[4] == 'single':
            input_name = cur_input[5]
    except Exception:
        pass

    return input_directory, input_name, input_category, input_hash, input_id


def parse_qbittorrent(args):
    # qbittorrent usage: C:\full\path\to\nzbToMedia\TorrentToMedia.py '%D|%N|%L|%I'
    try:
        cur_input = args[1].split('|')
    except Exception:
        cur_input = []
    try:
        input_directory = os.path.normpath(cur_input[0].replace('\'', ''))
    except Exception:
        input_directory = ''
    try:
        input_name = cur_input[1]
        if input_name[0] == '\'':
            input_name = input_name[1:]
        if input_name[-1] == '\'':
            input_name = input_name[:-1]
    except Exception:
        input_name = ''
    try:
        input_category = cur_input[2].replace('\'', '')
    except Exception:
        input_category = ''
    try:
        input_hash = cur_input[3].replace('\'', '')
    except Exception:
        input_hash = ''
    try:
        input_id = cur_input[3].replace('\'', '')
    except Exception:
        input_id = ''

    return input_directory, input_name, input_category, input_hash, input_id


def parse_args(client_agent, args):
    clients = {
        'other': parse_other,
        'rtorrent': parse_rtorrent,
        'utorrent': parse_utorrent,
        'deluge': parse_deluge,
        'transmission': parse_transmission,
        'qbittorrent': parse_qbittorrent,
        'vuze': parse_vuze,
        'synods': parse_synods,
    }

    try:
        return clients[client_agent](args)
    except Exception:
        return None, None, None, None, None
