from __future__ import annotations

import requests

from core.utils.common import clean_dir
from core.utils.common import flatten
from core.utils.common import get_dirs
from core.utils.common import process_dir
from core.utils.download_info import get_download_info
from core.utils.download_info import update_download_info_status
from core.utils.encoding import char_replace
from core.utils.encoding import convert_to_ascii
from core.utils.files import backup_versioned_file
from core.utils.files import extract_files
from core.utils.files import is_archive_file
from core.utils.files import is_media_file
from core.utils.files import is_min_size
from core.utils.files import list_media_files
from core.utils.files import move_file
from core.utils.identification import category_search
from core.utils.identification import find_imdbid
from core.utils.links import copy_link
from core.utils.links import replace_links
from core.utils.naming import clean_file_name
from core.utils.naming import is_sample
from core.utils.naming import sanitize_name
from core.utils.network import find_download
from core.utils.network import server_responding
from core.utils.network import test_connection
from core.utils.network import wake_on_lan
from core.utils.network import wake_up
from core.utils.parsers import parse_args
from core.utils.parsers import parse_deluge
from core.utils.parsers import parse_other
from core.utils.parsers import parse_qbittorrent
from core.utils.parsers import parse_rtorrent
from core.utils.parsers import parse_transmission
from core.utils.parsers import parse_utorrent
from core.utils.parsers import parse_vuze
from core.utils.paths import clean_directory
from core.utils.paths import flatten_dir
from core.utils.paths import get_dir_size
from core.utils.paths import make_dir
from core.utils.paths import onerror
from core.utils.paths import rchmod
from core.utils.paths import remote_dir
from core.utils.paths import remove_dir
from core.utils.paths import remove_empty_folders
from core.utils.paths import remove_read_only
from core.utils.processes import restart
from core.utils.processes import RunningProcess

requests.packages.urllib3.disable_warnings()
