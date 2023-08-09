# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import itertools
import locale
import os
import platform
import re
import subprocess
import sys
import time

import eol
import libs.autoload
import libs.util

if not libs.autoload.completed:
    sys.exit('Could not load vendored libraries.')

try:
    import win32event
except ImportError:
    if sys.platform == 'win32':
        sys.exit('Please install pywin32')

APP_ROOT = libs.util.module_path(parent=True)
SOURCE_ROOT = libs.util.module_path()

# init preliminaries
SYS_ARGV = sys.argv[1:]
APP_FILENAME = sys.argv[0]
APP_NAME = os.path.basename(APP_FILENAME)
LOG_DIR = os.path.join(APP_ROOT, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'nzbtomedia.log')
PID_FILE = os.path.join(LOG_DIR, 'nzbtomedia.pid')
CONFIG_FILE = os.path.join(APP_ROOT, 'autoProcessMedia.cfg')
CONFIG_SPEC_FILE = os.path.join(APP_ROOT, 'autoProcessMedia.cfg.spec')
CONFIG_MOVIE_FILE = os.path.join(APP_ROOT, 'autoProcessMovie.cfg')
CONFIG_TV_FILE = os.path.join(APP_ROOT, 'autoProcessTv.cfg')
TEST_FILE = os.path.join(APP_ROOT, 'tests', 'test.mp4')
MYAPP = None

import six
from six.moves import reload_module

from core import logger, main_db, version_check, databases, transcoder
from core.configuration import config
from core.plugins.downloaders.configuration import (
    configure_nzbs,
    configure_torrents,
    configure_torrent_class,
)
from core.plugins.downloaders.utils import (
    pause_torrent,
    remove_torrent,
    resume_torrent,
)
from core.plugins.plex import configure_plex
from core.utils import (
    RunningProcess,
    category_search,
    clean_dir,
    copy_link,
    extract_files,
    flatten,
    get_dirs,
    get_download_info,
    list_media_files,
    make_dir,
    parse_args,
    rchmod,
    remove_dir,
    remove_read_only,
    restart,
    sanitize_name,
    update_download_info_status,
    wake_up,
)

__version__ = '12.1.12'

# Client Agents
NZB_CLIENTS = ['sabnzbd', 'nzbget', 'manual']
TORRENT_CLIENTS = ['transmission', 'deluge', 'utorrent', 'rtorrent', 'qbittorrent', 'other', 'manual']

# sickbeard fork/branch constants
FORK_DEFAULT = 'default'
FORK_FAILED = 'failed'
FORK_FAILED_TORRENT = 'failed-torrent'
FORK_SICKCHILL = 'SickChill'
FORK_SICKCHILL_API = 'SickChill-api'
FORK_SICKBEARD_API = 'SickBeard-api'
FORK_MEDUSA = 'Medusa'
FORK_MEDUSA_API = 'Medusa-api'
FORK_MEDUSA_APIV2 = 'Medusa-apiv2'
FORK_SICKGEAR = 'SickGear'
FORK_SICKGEAR_API = 'SickGear-api'
FORK_STHENO = 'Stheno'

FORKS = {
    FORK_DEFAULT: {'dir': None},
    FORK_FAILED: {'dirName': None, 'failed': None},
    FORK_FAILED_TORRENT: {'dir': None, 'failed': None, 'process_method': None},
    FORK_SICKCHILL: {'proc_dir': None, 'failed': None, 'process_method': None, 'force': None, 'delete_on': None, 'force_next': None},
    FORK_SICKCHILL_API: {'path': None, 'proc_dir': None, 'failed': None, 'process_method': None, 'force': None, 'force_replace': None, 'return_data': None, 'type': None, 'delete': None, 'force_next': None, 'is_priority': None, 'cmd': 'postprocess'},
    FORK_SICKBEARD_API: {'path': None, 'failed': None, 'process_method': None, 'force_replace': None, 'return_data': None, 'type': None, 'delete': None, 'force_next': None, 'cmd': 'postprocess'},
    FORK_MEDUSA: {'proc_dir': None, 'failed': None, 'process_method': None, 'force': None, 'delete_on': None, 'ignore_subs': None},
    FORK_MEDUSA_API: {'path': None, 'failed': None, 'process_method': None, 'force_replace': None, 'return_data': None, 'type': None, 'delete_files': None, 'is_priority': None, 'cmd': 'postprocess'},
    FORK_MEDUSA_APIV2: {'proc_dir': None, 'resource': None, 'failed': None, 'process_method': None, 'force': None, 'type': None, 'delete_on': None, 'is_priority': None},
    FORK_SICKGEAR: {'dir': None, 'failed': None, 'process_method': None, 'force': None},
    FORK_SICKGEAR_API: {'path': None, 'process_method': None, 'force_replace': None, 'return_data': None, 'type': None, 'is_priority': None, 'failed': None, 'cmd': 'sg.postprocess'},
    FORK_STHENO: {'proc_dir': None, 'failed': None, 'process_method': None, 'force': None, 'delete_on': None, 'ignore_subs': None},
}
ALL_FORKS = {k: None for k in set(list(itertools.chain.from_iterable([FORKS[x].keys() for x in FORKS.keys()])))}

# SiCKRAGE OAuth2
SICKRAGE_OAUTH_CLIENT_ID = 'nzbtomedia'
SICKRAGE_OAUTH_TOKEN_URL = 'https://auth.sickrage.ca/realms/sickrage/protocol/openid-connect/token'

# NZBGet Exit Codes
NZBGET_POSTPROCESS_PAR_CHECK = 92
NZBGET_POSTPROCESS_SUCCESS = 93
NZBGET_POSTPROCESS_ERROR = 94
NZBGET_POSTPROCESS_NONE = 95

CFG = None
LOG_DEBUG = None
LOG_DB = None
LOG_ENV = None
LOG_GIT = None
SYS_ENCODING = None
FAILED = False

AUTO_UPDATE = None
NZBTOMEDIA_VERSION = __version__
NEWEST_VERSION = None
NEWEST_VERSION_STRING = None
VERSION_NOTIFY = None
GIT_PATH = None
GIT_USER = None
GIT_BRANCH = None
GIT_REPO = None
FORCE_CLEAN = None
SAFE_MODE = None
NOEXTRACTFAILED = None

NZB_CLIENT_AGENT = None
SABNZBD_HOST = None
SABNZBD_PORT = None
SABNZBD_APIKEY = None
NZB_DEFAULT_DIRECTORY = None

TORRENT_CLIENT_AGENT = None
TORRENT_CLASS = None
USE_LINK = None
OUTPUT_DIRECTORY = None
NOFLATTEN = []
DELETE_ORIGINAL = None
TORRENT_CHMOD_DIRECTORY = None
TORRENT_DEFAULT_DIRECTORY = None
TORRENT_RESUME = None
TORRENT_RESUME_ON_FAILURE = None

REMOTE_PATHS = []

UTORRENT_WEB_UI = None
UTORRENT_USER = None
UTORRENT_PASSWORD = None

TRANSMISSION_HOST = None
TRANSMISSION_PORT = None
TRANSMISSION_USER = None
TRANSMISSION_PASSWORD = None

SYNO_HOST = None
SYNO_PORT = None
SYNO_USER = None
SYNO_PASSWORD = None

DELUGE_HOST = None
DELUGE_PORT = None
DELUGE_USER = None
DELUGE_PASSWORD = None

QBITTORRENT_HOST = None
QBITTORRENT_PORT = None
QBITTORRENT_USER = None
QBITTORRENT_PASSWORD = None

PLEX_SSL = None
PLEX_HOST = None
PLEX_PORT = None
PLEX_TOKEN = None
PLEX_SECTION = []

EXT_CONTAINER = []
COMPRESSED_CONTAINER = []
MEDIA_CONTAINER = []
AUDIO_CONTAINER = []
META_CONTAINER = []

SECTIONS = []
CATEGORIES = []
FORK_SET = []

MOUNTED = None
GETSUBS = False
TRANSCODE = None
CONCAT = None
FFMPEG_PATH = None
SYS_PATH = None
DUPLICATE = None
IGNOREEXTENSIONS = []
VEXTENSION = None
OUTPUTVIDEOPATH = None
PROCESSOUTPUT = False
GENERALOPTS = []
OTHEROPTS = []
ALANGUAGE = None
AINCLUDE = False
SLANGUAGES = []
SINCLUDE = False
SUBSDIR = None
ALLOWSUBS = False
SEXTRACT = False
SEMBED = False
BURN = False
DEFAULTS = None
VCODEC = None
VCODEC_ALLOW = []
VPRESET = None
VFRAMERATE = None
VBITRATE = None
VLEVEL = None
VCRF = None
VRESOLUTION = None
ACODEC = None
ACODEC_ALLOW = []
ACHANNELS = None
ABITRATE = None
ACODEC2 = None
ACODEC2_ALLOW = []
ACHANNELS2 = None
ABITRATE2 = None
ACODEC3 = None
ACODEC3_ALLOW = []
ACHANNELS3 = None
ABITRATE3 = None
SCODEC = None
OUTPUTFASTSTART = None
OUTPUTQUALITYPERCENT = None
FFMPEG = None
SEVENZIP = None
SHOWEXTRACT = 0
PAR2CMD = None
FFPROBE = None
CHECK_MEDIA = None
REQUIRE_LAN = None
NICENESS = []
HWACCEL = False

PASSWORDS_FILE = None
DOWNLOAD_INFO = None
GROUPS = None

USER_SCRIPT_MEDIAEXTENSIONS = None
USER_SCRIPT = None
USER_SCRIPT_PARAM = None
USER_SCRIPT_SUCCESSCODES = None
USER_SCRIPT_CLEAN = None
USER_DELAY = None
USER_SCRIPT_RUNONCE = None

__INITIALIZED__ = False


def configure_logging():
    global LOG_FILE
    global LOG_DIR

    if 'NTM_LOGFILE' in os.environ:
        LOG_FILE = os.environ['NTM_LOGFILE']
        LOG_DIR = os.path.split(LOG_FILE)[0]

    if not make_dir(LOG_DIR):
        print('No log folder, logging to screen only')


def configure_process():
    global MYAPP

    MYAPP = RunningProcess()
    while MYAPP.alreadyrunning():
        print('Waiting for existing session to end')
        time.sleep(30)


def configure_locale():
    global SYS_ENCODING

    try:
        locale.setlocale(locale.LC_ALL, '')
        SYS_ENCODING = locale.getpreferredencoding()
    except (locale.Error, IOError):
        pass

    # For OSes that are poorly configured I'll just randomly force UTF-8
    if not SYS_ENCODING or SYS_ENCODING in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
        SYS_ENCODING = 'UTF-8'

    if six.PY2:
        if not hasattr(sys, 'setdefaultencoding'):
            reload_module(sys)

        try:
            # pylint: disable=E1101
            # On non-unicode builds this will raise an AttributeError, if encoding type is not valid it throws a LookupError
            sys.setdefaultencoding(SYS_ENCODING)
        except Exception:
            print('Sorry, you MUST add the nzbToMedia folder to the PYTHONPATH environment variable'
                  '\nor find another way to force Python to use {codec} for string encoding.'.format
                  (codec=SYS_ENCODING))
            if 'NZBOP_SCRIPTDIR' in os.environ:
                sys.exit(NZBGET_POSTPROCESS_ERROR)
            else:
                sys.exit(1)


def configure_migration():
    global CONFIG_FILE
    global CFG

    # run migrate to convert old cfg to new style cfg plus fix any cfg missing values/options.
    if not config.migrate():
        logger.error('Unable to migrate config file {0}, exiting ...'.format(CONFIG_FILE))
        if 'NZBOP_SCRIPTDIR' in os.environ:
            pass  # We will try and read config from Environment.
        else:
            sys.exit(-1)

    # run migrate to convert NzbGet data from old cfg style to new cfg style
    if 'NZBOP_SCRIPTDIR' in os.environ:
        CFG = config.addnzbget()

    else:  # load newly migrated config
        logger.info('Loading config from [{0}]'.format(CONFIG_FILE))
        CFG = config()


def configure_logging_part_2():
    global LOG_DB
    global LOG_DEBUG
    global LOG_ENV
    global LOG_GIT

    # Enable/Disable DEBUG Logging
    LOG_DB = int(CFG['General']['log_db'])
    LOG_DEBUG = int(CFG['General']['log_debug'])
    LOG_ENV = int(CFG['General']['log_env'])
    LOG_GIT = int(CFG['General']['log_git'])

    if LOG_ENV:
        for item in os.environ:
            logger.info('{0}: {1}'.format(item, os.environ[item]), 'ENVIRONMENT')


def configure_general():
    global VERSION_NOTIFY
    global GIT_REPO
    global GIT_PATH
    global GIT_USER
    global GIT_BRANCH
    global FORCE_CLEAN
    global FFMPEG_PATH
    global SYS_PATH
    global CHECK_MEDIA
    global REQUIRE_LAN
    global SAFE_MODE
    global NOEXTRACTFAILED

    # Set Version and GIT variables
    VERSION_NOTIFY = int(CFG['General']['version_notify'])
    GIT_REPO = 'nzbToMedia'
    GIT_PATH = CFG['General']['git_path']
    GIT_USER = CFG['General']['git_user'] or 'clinton-hall'
    GIT_BRANCH = CFG['General']['git_branch'] or 'master'
    FORCE_CLEAN = int(CFG['General']['force_clean'])
    FFMPEG_PATH = CFG['General']['ffmpeg_path']
    SYS_PATH = CFG['General']['sys_path']
    CHECK_MEDIA = int(CFG['General']['check_media'])
    REQUIRE_LAN = None if not CFG['General']['require_lan'] else CFG['General']['require_lan'].split(',')
    SAFE_MODE = int(CFG['General']['safe_mode'])
    NOEXTRACTFAILED = int(CFG['General']['no_extract_failed'])


def configure_updates():
    global AUTO_UPDATE
    global MYAPP

    AUTO_UPDATE = int(CFG['General']['auto_update'])
    version_checker = version_check.CheckVersion()

    # Check for updates via GitHUB
    if version_checker.check_for_new_version() and AUTO_UPDATE:
        logger.info('Auto-Updating nzbToMedia, Please wait ...')
        if version_checker.update():
            # restart nzbToMedia
            try:
                del MYAPP
            except Exception:
                pass
            restart()
        else:
            logger.error('Update failed, not restarting. Check your log for more information.')

    # Set Current Version
    logger.info('nzbToMedia Version:{version} Branch:{branch} ({system} {release})'.format
                (version=NZBTOMEDIA_VERSION, branch=GIT_BRANCH,
                 system=platform.system(), release=platform.release()))


def configure_wake_on_lan():
    if int(CFG['WakeOnLan']['wake']):
        wake_up()


def configure_groups():
    global GROUPS

    GROUPS = CFG['Custom']['remove_group']

    if isinstance(GROUPS, str):
        GROUPS = GROUPS.split(',')

    if GROUPS == ['']:
        GROUPS = None


def configure_remote_paths():
    global REMOTE_PATHS

    REMOTE_PATHS = CFG['Network']['mount_points'] or []

    if REMOTE_PATHS:
        if isinstance(REMOTE_PATHS, list):
            REMOTE_PATHS = ','.join(REMOTE_PATHS)  # fix in case this imported as list.

        REMOTE_PATHS = (
            # /volume1/Public/,E:\|/volume2/share/,\\NAS\
            tuple(item.split(','))
            for item in REMOTE_PATHS.split('|')
        )

        REMOTE_PATHS = [
            # strip trailing and leading whitespaces
            (local.strip(), remote.strip())
            for local, remote in REMOTE_PATHS
        ]


def configure_niceness():
    global NICENESS

    with open(os.devnull, 'w') as devnull:
        try:
            subprocess.Popen(['nice'], stdout=devnull, stderr=devnull).communicate()
            if len(CFG['Posix']['niceness'].split(',')) > 1: #Allow passing of absolute command, not just value.
                NICENESS.extend(CFG['Posix']['niceness'].split(','))
            else:
                NICENESS.extend(['nice', '-n{0}'.format(int(CFG['Posix']['niceness']))])
        except Exception:
            pass
        try:
            subprocess.Popen(['ionice'], stdout=devnull, stderr=devnull).communicate()
            try:
                NICENESS.extend(['ionice', '-c{0}'.format(int(CFG['Posix']['ionice_class']))])
            except Exception:
                pass
            try:
                if 'ionice' in NICENESS:
                    NICENESS.extend(['-n{0}'.format(int(CFG['Posix']['ionice_classdata']))])
                else:
                    NICENESS.extend(['ionice', '-n{0}'.format(int(CFG['Posix']['ionice_classdata']))])
            except Exception:
                pass
        except Exception:
            pass


def configure_containers():
    global COMPRESSED_CONTAINER
    global MEDIA_CONTAINER
    global AUDIO_CONTAINER
    global META_CONTAINER

    COMPRESSED_CONTAINER = [re.compile(r'.r\d{2}$', re.I),
                            re.compile(r'.part\d+.rar$', re.I),
                            re.compile('.rar$', re.I)]
    COMPRESSED_CONTAINER += [re.compile('{0}$'.format(ext), re.I) for ext in
                             CFG['Extensions']['compressedExtensions']]
    MEDIA_CONTAINER = CFG['Extensions']['mediaExtensions']
    AUDIO_CONTAINER = CFG['Extensions']['audioExtensions']
    META_CONTAINER = CFG['Extensions']['metaExtensions']  # .nfo,.sub,.srt

    if isinstance(COMPRESSED_CONTAINER, str):
        COMPRESSED_CONTAINER = COMPRESSED_CONTAINER.split(',')

    if isinstance(MEDIA_CONTAINER, str):
        MEDIA_CONTAINER = MEDIA_CONTAINER.split(',')

    if isinstance(AUDIO_CONTAINER, str):
        AUDIO_CONTAINER = AUDIO_CONTAINER.split(',')

    if isinstance(META_CONTAINER, str):
        META_CONTAINER = META_CONTAINER.split(',')


def configure_transcoder():
    global MOUNTED
    global GETSUBS
    global TRANSCODE
    global DUPLICATE
    global CONCAT
    global IGNOREEXTENSIONS
    global OUTPUTFASTSTART
    global GENERALOPTS
    global OTHEROPTS
    global OUTPUTQUALITYPERCENT
    global OUTPUTVIDEOPATH
    global PROCESSOUTPUT
    global ALANGUAGE
    global AINCLUDE
    global SLANGUAGES
    global SINCLUDE
    global SEXTRACT
    global SEMBED
    global SUBSDIR
    global VEXTENSION
    global VCODEC
    global VPRESET
    global VFRAMERATE
    global VBITRATE
    global VRESOLUTION
    global VCRF
    global VLEVEL
    global VCODEC_ALLOW
    global ACODEC
    global ACODEC_ALLOW
    global ACHANNELS
    global ABITRATE
    global ACODEC2
    global ACODEC2_ALLOW
    global ACHANNELS2
    global ABITRATE2
    global ACODEC3
    global ACODEC3_ALLOW
    global ACHANNELS3
    global ABITRATE3
    global SCODEC
    global BURN
    global HWACCEL
    global ALLOWSUBS
    global DEFAULTS

    MOUNTED = None
    GETSUBS = int(CFG['Transcoder']['getSubs'])
    TRANSCODE = int(CFG['Transcoder']['transcode'])
    DUPLICATE = int(CFG['Transcoder']['duplicate'])
    CONCAT = int(CFG['Transcoder']['concat'])
    IGNOREEXTENSIONS = (CFG['Transcoder']['ignoreExtensions'])
    if isinstance(IGNOREEXTENSIONS, str):
        IGNOREEXTENSIONS = IGNOREEXTENSIONS.split(',')
    OUTPUTFASTSTART = int(CFG['Transcoder']['outputFastStart'])
    GENERALOPTS = (CFG['Transcoder']['generalOptions'])
    if isinstance(GENERALOPTS, str):
        GENERALOPTS = GENERALOPTS.split(',')
    if GENERALOPTS == ['']:
        GENERALOPTS = []
    if '-fflags' not in GENERALOPTS:
        GENERALOPTS.append('-fflags')
    if '+genpts' not in GENERALOPTS:
        GENERALOPTS.append('+genpts')
    OTHEROPTS = (CFG['Transcoder']['otherOptions'])
    if isinstance(OTHEROPTS, str):
        OTHEROPTS = OTHEROPTS.split(',')
    if OTHEROPTS == ['']:
        OTHEROPTS = []
    try:
        OUTPUTQUALITYPERCENT = int(CFG['Transcoder']['outputQualityPercent'])
    except Exception:
        pass
    OUTPUTVIDEOPATH = CFG['Transcoder']['outputVideoPath']
    PROCESSOUTPUT = int(CFG['Transcoder']['processOutput'])
    ALANGUAGE = CFG['Transcoder']['audioLanguage']
    AINCLUDE = int(CFG['Transcoder']['allAudioLanguages'])
    SLANGUAGES = CFG['Transcoder']['subLanguages']
    if isinstance(SLANGUAGES, str):
        SLANGUAGES = SLANGUAGES.split(',')
    if SLANGUAGES == ['']:
        SLANGUAGES = []
    SINCLUDE = int(CFG['Transcoder']['allSubLanguages'])
    SEXTRACT = int(CFG['Transcoder']['extractSubs'])
    SEMBED = int(CFG['Transcoder']['embedSubs'])
    SUBSDIR = CFG['Transcoder']['externalSubDir']
    VEXTENSION = CFG['Transcoder']['outputVideoExtension'].strip()
    VCODEC = CFG['Transcoder']['outputVideoCodec'].strip()
    VCODEC_ALLOW = CFG['Transcoder']['VideoCodecAllow'].strip()
    if isinstance(VCODEC_ALLOW, str):
        VCODEC_ALLOW = VCODEC_ALLOW.split(',')
    if VCODEC_ALLOW == ['']:
        VCODEC_ALLOW = []
    VPRESET = CFG['Transcoder']['outputVideoPreset'].strip()
    try:
        VFRAMERATE = float(CFG['Transcoder']['outputVideoFramerate'].strip())
    except Exception:
        pass
    try:
        VCRF = int(CFG['Transcoder']['outputVideoCRF'].strip())
    except Exception:
        pass
    try:
        VLEVEL = CFG['Transcoder']['outputVideoLevel'].strip()
    except Exception:
        pass
    try:
        VBITRATE = int((CFG['Transcoder']['outputVideoBitrate'].strip()).replace('k', '000'))
    except Exception:
        pass
    VRESOLUTION = CFG['Transcoder']['outputVideoResolution']
    ACODEC = CFG['Transcoder']['outputAudioCodec'].strip()
    ACODEC_ALLOW = CFG['Transcoder']['AudioCodecAllow'].strip()
    if isinstance(ACODEC_ALLOW, str):
        ACODEC_ALLOW = ACODEC_ALLOW.split(',')
    if ACODEC_ALLOW == ['']:
        ACODEC_ALLOW = []
    try:
        ACHANNELS = int(CFG['Transcoder']['outputAudioChannels'].strip())
    except Exception:
        pass
    try:
        ABITRATE = int((CFG['Transcoder']['outputAudioBitrate'].strip()).replace('k', '000'))
    except Exception:
        pass
    ACODEC2 = CFG['Transcoder']['outputAudioTrack2Codec'].strip()
    ACODEC2_ALLOW = CFG['Transcoder']['AudioCodec2Allow'].strip()
    if isinstance(ACODEC2_ALLOW, str):
        ACODEC2_ALLOW = ACODEC2_ALLOW.split(',')
    if ACODEC2_ALLOW == ['']:
        ACODEC2_ALLOW = []
    try:
        ACHANNELS2 = int(CFG['Transcoder']['outputAudioTrack2Channels'].strip())
    except Exception:
        pass
    try:
        ABITRATE2 = int((CFG['Transcoder']['outputAudioTrack2Bitrate'].strip()).replace('k', '000'))
    except Exception:
        pass
    ACODEC3 = CFG['Transcoder']['outputAudioOtherCodec'].strip()
    ACODEC3_ALLOW = CFG['Transcoder']['AudioOtherCodecAllow'].strip()
    if isinstance(ACODEC3_ALLOW, str):
        ACODEC3_ALLOW = ACODEC3_ALLOW.split(',')
    if ACODEC3_ALLOW == ['']:
        ACODEC3_ALLOW = []
    try:
        ACHANNELS3 = int(CFG['Transcoder']['outputAudioOtherChannels'].strip())
    except Exception:
        pass
    try:
        ABITRATE3 = int((CFG['Transcoder']['outputAudioOtherBitrate'].strip()).replace('k', '000'))
    except Exception:
        pass
    SCODEC = CFG['Transcoder']['outputSubtitleCodec'].strip()
    BURN = int(CFG['Transcoder']['burnInSubtitle'].strip())
    DEFAULTS = CFG['Transcoder']['outputDefault'].strip()
    HWACCEL = int(CFG['Transcoder']['hwAccel'])

    allow_subs = ['.mkv', '.mp4', '.m4v', 'asf', 'wma', 'wmv']
    codec_alias = {
        'libx264': ['libx264', 'h264', 'h.264', 'AVC', 'MPEG-4'],
        'libmp3lame': ['libmp3lame', 'mp3'],
        'libfaac': ['libfaac', 'aac', 'faac'],
    }
    transcode_defaults = {
        'iPad': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': None, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
        'iPad-1080p': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '1920:1080', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': None, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
        'iPad-720p': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '1280:720', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': None, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
        'Apple-TV': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '1280:720', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'ac3', 'ACODEC_ALLOW': ['ac3'], 'ABITRATE': None, 'ACHANNELS': 6,
            'ACODEC2': 'aac', 'ACODEC2_ALLOW': ['libfaac'], 'ABITRATE2': None, 'ACHANNELS2': 2,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
        'iPod': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '1280:720', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2,
            'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
        'iPhone': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '460:320', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2,
            'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
        'PS3': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'ac3', 'ACODEC_ALLOW': ['ac3'], 'ABITRATE': None, 'ACHANNELS': 6,
            'ACODEC2': 'aac', 'ACODEC2_ALLOW': ['libfaac'], 'ABITRATE2': None, 'ACHANNELS2': 2,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
        'xbox': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'ac3', 'ACODEC_ALLOW': ['ac3'], 'ABITRATE': None, 'ACHANNELS': 6,
            'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
        'Roku-480p': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
        'Roku-720p': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
        'Roku-1080p': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 160000, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
        'mkv': {
            'VEXTENSION': '.mkv', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4', 'mpeg2video'],
            'ACODEC': 'dts', 'ACODEC_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE': None, 'ACHANNELS': 8,
            'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None,
            'ACODEC3': 'ac3', 'ACODEC3_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE3': None, 'ACHANNELS3': 8,
            'SCODEC': 'mov_text'
        },
        'mkv-bluray': {
            'VEXTENSION': '.mkv', 'VCODEC': 'libx265', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'hevc', 'h265', 'libx265', 'h.265', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4', 'mpeg2video'],
            'ACODEC': 'dts', 'ACODEC_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE': None, 'ACHANNELS': 8,
            'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None,
            'ACODEC3': 'ac3', 'ACODEC3_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE3': None, 'ACHANNELS3': 8,
            'SCODEC': 'mov_text',
        },
        'mp4-scene-release': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': 19, 'VLEVEL': '3.1',
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4', 'mpeg2video'],
            'ACODEC': 'dts', 'ACODEC_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE': None, 'ACHANNELS': 8,
            'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None,
            'ACODEC3': 'ac3', 'ACODEC3_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE3': None, 'ACHANNELS3': 8,
            'SCODEC': 'mov_text',
        },
        'MKV-SD': {
            'VEXTENSION': '.mkv', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': '1200k', 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '720: -1', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text',
        },
    }
    if DEFAULTS and DEFAULTS in transcode_defaults:
        VEXTENSION = transcode_defaults[DEFAULTS]['VEXTENSION']
        VCODEC = transcode_defaults[DEFAULTS]['VCODEC']
        VPRESET = transcode_defaults[DEFAULTS]['VPRESET']
        VFRAMERATE = transcode_defaults[DEFAULTS]['VFRAMERATE']
        VBITRATE = transcode_defaults[DEFAULTS]['VBITRATE']
        VRESOLUTION = transcode_defaults[DEFAULTS]['VRESOLUTION']
        VCRF = transcode_defaults[DEFAULTS]['VCRF']
        VLEVEL = transcode_defaults[DEFAULTS]['VLEVEL']
        VCODEC_ALLOW = transcode_defaults[DEFAULTS]['VCODEC_ALLOW']
        ACODEC = transcode_defaults[DEFAULTS]['ACODEC']
        ACODEC_ALLOW = transcode_defaults[DEFAULTS]['ACODEC_ALLOW']
        ACHANNELS = transcode_defaults[DEFAULTS]['ACHANNELS']
        ABITRATE = transcode_defaults[DEFAULTS]['ABITRATE']
        ACODEC2 = transcode_defaults[DEFAULTS]['ACODEC2']
        ACODEC2_ALLOW = transcode_defaults[DEFAULTS]['ACODEC2_ALLOW']
        ACHANNELS2 = transcode_defaults[DEFAULTS]['ACHANNELS2']
        ABITRATE2 = transcode_defaults[DEFAULTS]['ABITRATE2']
        ACODEC3 = transcode_defaults[DEFAULTS]['ACODEC3']
        ACODEC3_ALLOW = transcode_defaults[DEFAULTS]['ACODEC3_ALLOW']
        ACHANNELS3 = transcode_defaults[DEFAULTS]['ACHANNELS3']
        ABITRATE3 = transcode_defaults[DEFAULTS]['ABITRATE3']
        SCODEC = transcode_defaults[DEFAULTS]['SCODEC']
    transcode_defaults = {}  # clear memory
    if transcode_defaults in ['mp4-scene-release'] and not OUTPUTQUALITYPERCENT:
        OUTPUTQUALITYPERCENT = 100

    if VEXTENSION in allow_subs:
        ALLOWSUBS = 1
    if not VCODEC_ALLOW and VCODEC:
        VCODEC_ALLOW.extend([VCODEC])
    for codec in VCODEC_ALLOW:
        if codec in codec_alias:
            extra = [item for item in codec_alias[codec] if item not in VCODEC_ALLOW]
            VCODEC_ALLOW.extend(extra)
    if not ACODEC_ALLOW and ACODEC:
        ACODEC_ALLOW.extend([ACODEC])
    for codec in ACODEC_ALLOW:
        if codec in codec_alias:
            extra = [item for item in codec_alias[codec] if item not in ACODEC_ALLOW]
            ACODEC_ALLOW.extend(extra)
    if not ACODEC2_ALLOW and ACODEC2:
        ACODEC2_ALLOW.extend([ACODEC2])
    for codec in ACODEC2_ALLOW:
        if codec in codec_alias:
            extra = [item for item in codec_alias[codec] if item not in ACODEC2_ALLOW]
            ACODEC2_ALLOW.extend(extra)
    if not ACODEC3_ALLOW and ACODEC3:
        ACODEC3_ALLOW.extend([ACODEC3])
    for codec in ACODEC3_ALLOW:
        if codec in codec_alias:
            extra = [item for item in codec_alias[codec] if item not in ACODEC3_ALLOW]
            ACODEC3_ALLOW.extend(extra)


def configure_passwords_file():
    global PASSWORDS_FILE

    PASSWORDS_FILE = CFG['passwords']['PassWordFile']


def configure_sections(section):
    global SECTIONS
    global CATEGORIES
    # check for script-defied section and if None set to allow sections
    SECTIONS = CFG[
        tuple(x for x in CFG if CFG[x].sections and CFG[x].isenabled())
        if not section else (section,)
    ]
    for section, subsections in SECTIONS.items():
        CATEGORIES.extend([subsection for subsection in subsections if CFG[section][subsection].isenabled()])
    CATEGORIES = list(set(CATEGORIES))


def configure_utility_locations():
    global SHOWEXTRACT
    global SEVENZIP
    global FFMPEG
    global FFPROBE
    global PAR2CMD

    # Setup FFMPEG, FFPROBE and SEVENZIP locations
    if platform.system() == 'Windows':
        FFMPEG = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
        FFPROBE = os.path.join(FFMPEG_PATH, 'ffprobe.exe')
        SEVENZIP = os.path.join(APP_ROOT, 'core', 'extractor', 'bin', platform.machine(), '7z.exe')
        SHOWEXTRACT = int(str(CFG['Windows']['show_extraction']), 0)

        if not (os.path.isfile(FFMPEG)):  # problem
            FFMPEG = None
            logger.warning('Failed to locate ffmpeg.exe. Transcoding disabled!')
            logger.warning('Install ffmpeg with x264 support to enable this feature  ...')

        if not (os.path.isfile(FFPROBE)):
            FFPROBE = None
            if CHECK_MEDIA:
                logger.warning('Failed to locate ffprobe.exe. Video corruption detection disabled!')
                logger.warning('Install ffmpeg with x264 support to enable this feature  ...')

    else:
        if SYS_PATH:
            os.environ['PATH'] += ':' + SYS_PATH
        try:
            SEVENZIP = subprocess.Popen(['which', '7z'], stdout=subprocess.PIPE).communicate()[0].strip().decode()
        except Exception:
            pass
        if not SEVENZIP:
            try:
                SEVENZIP = subprocess.Popen(['which', '7zr'], stdout=subprocess.PIPE).communicate()[0].strip().decode()
            except Exception:
                pass
        if not SEVENZIP:
            try:
                SEVENZIP = subprocess.Popen(['which', '7za'], stdout=subprocess.PIPE).communicate()[0].strip().decode()
            except Exception:
                pass
        if not SEVENZIP:
            SEVENZIP = None
            logger.warning(
                'Failed to locate 7zip. Transcoding of disk images and extraction of .7z files will not be possible!')
        try:
            PAR2CMD = subprocess.Popen(['which', 'par2'], stdout=subprocess.PIPE).communicate()[0].strip().decode()
        except Exception:
            pass
        if not PAR2CMD:
            PAR2CMD = None
            logger.warning(
                'Failed to locate par2. Repair and rename using par files will not be possible!')
        if os.path.isfile(os.path.join(FFMPEG_PATH, 'ffmpeg')) or os.access(os.path.join(FFMPEG_PATH, 'ffmpeg'),
                                                                            os.X_OK):
            FFMPEG = os.path.join(FFMPEG_PATH, 'ffmpeg')
        elif os.path.isfile(os.path.join(FFMPEG_PATH, 'avconv')) or os.access(os.path.join(FFMPEG_PATH, 'avconv'),
                                                                              os.X_OK):
            FFMPEG = os.path.join(FFMPEG_PATH, 'avconv')
        else:
            try:
                FFMPEG = subprocess.Popen(['which', 'ffmpeg'], stdout=subprocess.PIPE).communicate()[0].strip().decode()
            except Exception:
                pass
            if not FFMPEG:
                try:
                    FFMPEG = subprocess.Popen(['which', 'avconv'], stdout=subprocess.PIPE).communicate()[0].strip().decode()
                except Exception:
                    pass
        if not FFMPEG:
            FFMPEG = None
            logger.warning('Failed to locate ffmpeg. Transcoding disabled!')
            logger.warning('Install ffmpeg with x264 support to enable this feature  ...')

        if os.path.isfile(os.path.join(FFMPEG_PATH, 'ffprobe')) or os.access(os.path.join(FFMPEG_PATH, 'ffprobe'),
                                                                             os.X_OK):
            FFPROBE = os.path.join(FFMPEG_PATH, 'ffprobe')
        elif os.path.isfile(os.path.join(FFMPEG_PATH, 'avprobe')) or os.access(os.path.join(FFMPEG_PATH, 'avprobe'),
                                                                               os.X_OK):
            FFPROBE = os.path.join(FFMPEG_PATH, 'avprobe')
        else:
            try:
                FFPROBE = subprocess.Popen(['which', 'ffprobe'], stdout=subprocess.PIPE).communicate()[0].strip().decode()
            except Exception:
                pass
            if not FFPROBE:
                try:
                    FFPROBE = subprocess.Popen(['which', 'avprobe'], stdout=subprocess.PIPE).communicate()[0].strip().decode()
                except Exception:
                    pass
        if not FFPROBE:
            FFPROBE = None
            if CHECK_MEDIA:
                logger.warning('Failed to locate ffprobe. Video corruption detection disabled!')
                logger.warning('Install ffmpeg with x264 support to enable this feature  ...')


def check_python():
    """Check End-of-Life status for Python version."""
    # Raise if end of life
    eol.check()

    # Warn if within grace period
    grace_period = 365  # days
    eol.warn_for_status(grace_period=-grace_period)

    # Log warning if within grace period
    days_left = eol.lifetime()
    if days_left > 0:
        logger.info(
            'Python v{major}.{minor} will reach end of life in {x} days.'.format(
                major=sys.version_info[0],
                minor=sys.version_info[1],
                x=days_left,
            ),
        )
    else:
        logger.info(
            'Python v{major}.{minor} reached end of life {x} days ago.'.format(
                major=sys.version_info[0],
                minor=sys.version_info[1],
                x=-days_left,
            ),
        )
    if days_left <= grace_period:
        logger.warning('Please upgrade to a more recent Python version.')


def initialize(section=None):
    global __INITIALIZED__

    if __INITIALIZED__:
        return False

    configure_logging()
    configure_process()
    configure_locale()

    # init logging
    logger.ntm_log_instance.init_logging()

    configure_migration()
    configure_logging_part_2()

    # check python version
    check_python()

    # initialize the main SB database
    main_db.upgrade_database(main_db.DBConnection(), databases.InitialSchema)

    configure_general()
    configure_updates()
    configure_wake_on_lan()
    configure_nzbs(CFG)
    configure_torrents(CFG)
    configure_remote_paths()
    configure_plex(CFG)
    configure_niceness()
    configure_containers()
    configure_transcoder()
    configure_passwords_file()
    configure_utility_locations()
    configure_sections(section)
    configure_torrent_class()
    configure_groups()

    __INITIALIZED__ = True

    # finished initializing
    return __INITIALIZED__
