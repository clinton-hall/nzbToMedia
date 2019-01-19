# coding=utf-8

from __future__ import print_function

import itertools
import locale
import os
import platform
import re
import subprocess
import sys
import time

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
from core.utils import (
    RunningProcess,
    category_search,
    clean_dir,
    copy_link,
    create_torrent_class,
    extract_files,
    flatten,
    get_dirs,
    get_download_info,
    list_media_files,
    make_dir,
    parse_args,
    pause_torrent,
    rchmod,
    remove_dir,
    remove_read_only,
    remove_torrent,
    restart,
    resume_torrent,
    sanitize_name,
    update_download_info_status,
    wake_up,
)

__version__ = '12.0.7'

# Client Agents
NZB_CLIENTS = ['sabnzbd', 'nzbget', 'manual']
TORRENT_CLIENTS = ['transmission', 'deluge', 'utorrent', 'rtorrent', 'qbittorrent', 'other', 'manual']

# sabnzbd constants
SABNZB_NO_OF_ARGUMENTS = 8
SABNZB_0717_NO_OF_ARGUMENTS = 9

# sickbeard fork/branch constants
FORK_DEFAULT = 'default'
FORK_FAILED = 'failed'
FORK_FAILED_TORRENT = 'failed-torrent'
FORK_SICKRAGE = 'SickRage'
FORK_SICKCHILL = 'SickChill'
FORK_SICKBEARD_API = 'SickBeard-api'
FORK_MEDUSA = 'Medusa'
FORK_SICKGEAR = 'SickGear'
FORK_STHENO = 'Stheno'

FORKS = {
    FORK_DEFAULT: {'dir': None},
    FORK_FAILED: {'dirName': None, 'failed': None},
    FORK_FAILED_TORRENT: {'dir': None, 'failed': None, 'process_method': None},
    FORK_SICKRAGE: {'proc_dir': None, 'failed': None, 'process_method': None, 'force': None, 'delete_on': None},
    FORK_SICKCHILL: {'proc_dir': None, 'failed': None, 'process_method': None, 'force': None, 'delete_on': None, 'force_next': None},
    FORK_SICKBEARD_API: {'path': None, 'failed': None, 'process_method': None, 'force_replace': None, 'return_data': None, 'type': None, 'delete': None, 'force_next': None},
    FORK_MEDUSA: {'proc_dir': None, 'failed': None, 'process_method': None, 'force': None, 'delete_on': None, 'ignore_subs': None},
    FORK_SICKGEAR: {'dir': None, 'failed': None, 'process_method': None, 'force': None},
    FORK_STHENO: {"proc_dir": None, "failed": None, "process_method": None, "force": None, "delete_on": None, "ignore_subs": None}
}
ALL_FORKS = {k: None for k in set(list(itertools.chain.from_iterable([FORKS[x].keys() for x in FORKS.keys()])))}

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

NZB_CLIENTAGENT = None
SABNZBDHOST = None
SABNZBDPORT = None
SABNZBDAPIKEY = None
NZB_DEFAULTDIR = None

TORRENT_CLIENTAGENT = None
TORRENT_CLASS = None
USELINK = None
OUTPUTDIRECTORY = None
NOFLATTEN = []
DELETE_ORIGINAL = None
TORRENT_CHMOD_DIRECTORY = None
TORRENT_DEFAULTDIR = None
TORRENT_RESUME = None
TORRENT_RESUME_ON_FAILURE = None

REMOTEPATHS = []

UTORRENT_WEB_UI = None
UTORRENT_USER = None
UTORRENT_PASSWORD = None

TRANSMISSION_HOST = None
TRANSMISSION_PORT = None
TRANSMISSION_USER = None
TRANSMISSION_PASSWORD = None

DELUGE_HOST = None
DELUGEPORT = None
DELUGEUSR = None
DELUGEPWD = None

QBITTORRENTHOST = None
QBITTORRENTPORT = None
QBITTORRENTUSR = None
QBITTORRENTPWD = None

PLEXSSL = None
PLEXHOST = None
PLEXPORT = None
PLEXTOKEN = None
PLEXSEC = []

EXTCONTAINER = []
COMPRESSEDCONTAINER = []
MEDIACONTAINER = []
AUDIOCONTAINER = []
METACONTAINER = []

SECTIONS = []
CATEGORIES = []

GETSUBS = False
TRANSCODE = None
CONCAT = None
FFMPEG_PATH = None
DUPLICATE = None
IGNOREEXTENSIONS = []
VEXTENSION = None
OUTPUTVIDEOPATH = None
PROCESSOUTPUT = False
GENERALOPTS = []
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
NICENESS = []
HWACCEL = False

PASSWORDSFILE = None
DOWNLOADINFO = None
GROUPS = None

USER_SCRIPT_MEDIAEXTENSIONS = None
USER_SCRIPT = None
USER_SCRIPT_PARAM = None
USER_SCRIPT_SUCCESSCODES = None
USER_SCRIPT_CLEAN = None
USER_DELAY = None
USER_SCRIPT_RUNONCE = None

__INITIALIZED__ = False


def initialize(section=None):
    global NZBGET_POSTPROCESS_ERROR, NZBGET_POSTPROCESS_NONE, NZBGET_POSTPROCESS_PAR_CHECK, NZBGET_POSTPROCESS_SUCCESS, \
        NZBTOMEDIA_TIMEOUT, FORKS, FORK_DEFAULT, FORK_FAILED_TORRENT, FORK_FAILED, NOEXTRACTFAILED, SHOWEXTRACT, \
        NZBTOMEDIA_BRANCH, NZBTOMEDIA_VERSION, NEWEST_VERSION, NEWEST_VERSION_STRING, VERSION_NOTIFY, SYS_ARGV, CFG, \
        SABNZB_NO_OF_ARGUMENTS, SABNZB_0717_NO_OF_ARGUMENTS, CATEGORIES, TORRENT_CLIENTAGENT, USELINK, OUTPUTDIRECTORY, \
        NOFLATTEN, UTORRENT_PASSWORD, UTORRENT_USER, UTORRENT_WEB_UI, DELUGE_HOST, DELUGEPORT, DELUGEUSR, DELUGEPWD, VLEVEL, \
        TRANSMISSION_HOST, TRANSMISSION_PORT, TRANSMISSION_PASSWORD, TRANSMISSION_USER, COMPRESSEDCONTAINER, MEDIACONTAINER, \
        METACONTAINER, SECTIONS, ALL_FORKS, TEST_FILE, GENERALOPTS, LOG_GIT, GROUPS, SEVENZIP, CONCAT, VCRF, \
        __INITIALIZED__, AUTO_UPDATE, APP_FILENAME, USER_DELAY, APP_NAME, TRANSCODE, DEFAULTS, GIT_PATH, GIT_USER, \
        GIT_BRANCH, GIT_REPO, SYS_ENCODING, NZB_CLIENTAGENT, SABNZBDHOST, SABNZBDPORT, SABNZBDAPIKEY, \
        DUPLICATE, IGNOREEXTENSIONS, VEXTENSION, OUTPUTVIDEOPATH, PROCESSOUTPUT, VCODEC, VCODEC_ALLOW, VPRESET, \
        VFRAMERATE, LOG_DB, VBITRATE, VRESOLUTION, ALANGUAGE, AINCLUDE, ACODEC, ACODEC_ALLOW, ABITRATE, FAILED, \
        ACODEC2, ACODEC2_ALLOW, ABITRATE2, ACODEC3, ACODEC3_ALLOW, ABITRATE3, ALLOWSUBS, SEXTRACT, SEMBED, SLANGUAGES, \
        SINCLUDE, SUBSDIR, SCODEC, OUTPUTFASTSTART, OUTPUTQUALITYPERCENT, BURN, GETSUBS, HWACCEL, LOG_DIR, LOG_FILE, \
        NICENESS, LOG_DEBUG, FORCE_CLEAN, FFMPEG_PATH, FFMPEG, FFPROBE, AUDIOCONTAINER, EXTCONTAINER, TORRENT_CLASS, \
        DELETE_ORIGINAL, TORRENT_CHMOD_DIRECTORY, PASSWORDSFILE, USER_DELAY, USER_SCRIPT, USER_SCRIPT_CLEAN, USER_SCRIPT_MEDIAEXTENSIONS, \
        USER_SCRIPT_PARAM, USER_SCRIPT_RUNONCE, USER_SCRIPT_SUCCESSCODES, DOWNLOADINFO, CHECK_MEDIA, SAFE_MODE, \
        TORRENT_DEFAULTDIR, TORRENT_RESUME_ON_FAILURE, NZB_DEFAULTDIR, REMOTEPATHS, LOG_ENV, PID_FILE, MYAPP, ACHANNELS, ACHANNELS2, ACHANNELS3, \
        PLEXSSL, PLEXHOST, PLEXPORT, PLEXTOKEN, PLEXSEC, TORRENT_RESUME, PAR2CMD, QBITTORRENTHOST, QBITTORRENTPORT, QBITTORRENTUSR, QBITTORRENTPWD

    if __INITIALIZED__:
        return False

    if 'NTM_LOGFILE' in os.environ:
        LOG_FILE = os.environ['NTM_LOGFILE']
        LOG_DIR = os.path.split(LOG_FILE)[0]

    if not make_dir(LOG_DIR):
        print('No log folder, logging to screen only')

    MYAPP = RunningProcess()
    while MYAPP.alreadyrunning():
        print('Waiting for existing session to end')
        time.sleep(30)

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

    # init logging
    logger.ntm_log_instance.init_logging()

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

    # Enable/Disable DEBUG Logging
    LOG_DEBUG = int(CFG['General']['log_debug'])
    LOG_DB = int(CFG['General']['log_db'])
    LOG_ENV = int(CFG['General']['log_env'])
    LOG_GIT = int(CFG['General']['log_git'])

    if LOG_ENV:
        for item in os.environ:
            logger.info('{0}: {1}'.format(item, os.environ[item]), 'ENVIRONMENT')

    # initialize the main SB database
    main_db.upgrade_database(main_db.DBConnection(), databases.InitialSchema)

    # Set Version and GIT variables
    VERSION_NOTIFY = int(CFG['General']['version_notify'])
    AUTO_UPDATE = int(CFG['General']['auto_update'])
    GIT_REPO = 'nzbToMedia'
    GIT_PATH = CFG['General']['git_path']
    GIT_USER = CFG['General']['git_user'] or 'clinton-hall'
    GIT_BRANCH = CFG['General']['git_branch'] or 'master'
    FORCE_CLEAN = int(CFG['General']['force_clean'])
    FFMPEG_PATH = CFG['General']['ffmpeg_path']
    CHECK_MEDIA = int(CFG['General']['check_media'])
    SAFE_MODE = int(CFG['General']['safe_mode'])
    NOEXTRACTFAILED = int(CFG['General']['no_extract_failed'])

    # Check for updates via GitHUB
    if version_check.CheckVersion().check_for_new_version():
        if AUTO_UPDATE == 1:
            logger.info('Auto-Updating nzbToMedia, Please wait ...')
            updated = version_check.CheckVersion().update()
            if updated:
                # restart nzbToMedia
                try:
                    del MYAPP
                except Exception:
                    pass
                restart()
            else:
                logger.error('Update wasn\'t successful, not restarting. Check your log for more information.')

    # Set Current Version
    logger.info('nzbToMedia Version:{version} Branch:{branch} ({system} {release})'.format
                (version=NZBTOMEDIA_VERSION, branch=GIT_BRANCH,
                 system=platform.system(), release=platform.release()))

    if int(CFG['WakeOnLan']['wake']) == 1:
        wake_up()

    NZB_CLIENTAGENT = CFG['Nzb']['clientAgent']  # sabnzbd
    SABNZBDHOST = CFG['Nzb']['sabnzbd_host']
    SABNZBDPORT = int(CFG['Nzb']['sabnzbd_port'] or 8080)  # defaults to accomodate NzbGet
    SABNZBDAPIKEY = CFG['Nzb']['sabnzbd_apikey']
    NZB_DEFAULTDIR = CFG['Nzb']['default_downloadDirectory']
    GROUPS = CFG['Custom']['remove_group']
    if isinstance(GROUPS, str):
        GROUPS = GROUPS.split(',')
    if GROUPS == ['']:
        GROUPS = None

    TORRENT_CLIENTAGENT = CFG['Torrent']['clientAgent']  # utorrent | deluge | transmission | rtorrent | vuze | qbittorrent |other
    USELINK = CFG['Torrent']['useLink']  # no | hard | sym
    OUTPUTDIRECTORY = CFG['Torrent']['outputDirectory']  # /abs/path/to/complete/
    TORRENT_DEFAULTDIR = CFG['Torrent']['default_downloadDirectory']
    CATEGORIES = (CFG['Torrent']['categories'])  # music,music_videos,pictures,software
    NOFLATTEN = (CFG['Torrent']['noFlatten'])
    if isinstance(NOFLATTEN, str):
        NOFLATTEN = NOFLATTEN.split(',')
    if isinstance(CATEGORIES, str):
        CATEGORIES = CATEGORIES.split(',')
    DELETE_ORIGINAL = int(CFG['Torrent']['deleteOriginal'])
    TORRENT_CHMOD_DIRECTORY = int(str(CFG['Torrent']['chmodDirectory']), 8)
    TORRENT_RESUME_ON_FAILURE = int(CFG['Torrent']['resumeOnFailure'])
    TORRENT_RESUME = int(CFG['Torrent']['resume'])
    UTORRENT_WEB_UI = CFG['Torrent']['uTorrentWEBui']  # http://localhost:8090/gui/
    UTORRENT_USER = CFG['Torrent']['uTorrentUSR']  # mysecretusr
    UTORRENT_PASSWORD = CFG['Torrent']['uTorrentPWD']  # mysecretpwr

    TRANSMISSION_HOST = CFG['Torrent']['TransmissionHost']  # localhost
    TRANSMISSION_PORT = int(CFG['Torrent']['TransmissionPort'])
    TRANSMISSION_USER = CFG['Torrent']['TransmissionUSR']  # mysecretusr
    TRANSMISSION_PASSWORD = CFG['Torrent']['TransmissionPWD']  # mysecretpwr

    DELUGE_HOST = CFG['Torrent']['DelugeHost']  # localhost
    DELUGEPORT = int(CFG['Torrent']['DelugePort'])  # 8084
    DELUGEUSR = CFG['Torrent']['DelugeUSR']  # mysecretusr
    DELUGEPWD = CFG['Torrent']['DelugePWD']  # mysecretpwr

    QBITTORRENTHOST = CFG['Torrent']['qBittorrenHost']  # localhost
    QBITTORRENTPORT = int(CFG['Torrent']['qBittorrentPort'])  # 8080
    QBITTORRENTUSR = CFG['Torrent']['qBittorrentUSR']  # mysecretusr
    QBITTORRENTPWD = CFG['Torrent']['qBittorrentPWD']  # mysecretpwr

    REMOTEPATHS = CFG['Network']['mount_points'] or []
    if REMOTEPATHS:
        if isinstance(REMOTEPATHS, list):
            REMOTEPATHS = ','.join(REMOTEPATHS)  # fix in case this imported as list.
        REMOTEPATHS = [tuple(item.split(',')) for item in
                       REMOTEPATHS.split('|')]  # /volume1/Public/,E:\|/volume2/share/,\\NAS\
        REMOTEPATHS = [(local.strip(), remote.strip()) for local, remote in
                       REMOTEPATHS]  # strip trailing and leading whitespaces

    PLEXSSL = int(CFG['Plex']['plex_ssl'])
    PLEXHOST = CFG['Plex']['plex_host']
    PLEXPORT = CFG['Plex']['plex_port']
    PLEXTOKEN = CFG['Plex']['plex_token']
    PLEXSEC = CFG['Plex']['plex_sections'] or []
    if PLEXSEC:
        if isinstance(PLEXSEC, list):
            PLEXSEC = ','.join(PLEXSEC)  # fix in case this imported as list.
        PLEXSEC = [tuple(item.split(',')) for item in PLEXSEC.split('|')]

    devnull = open(os.devnull, 'w')
    try:
        subprocess.Popen(['nice'], stdout=devnull, stderr=devnull).communicate()
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
    devnull.close()

    COMPRESSEDCONTAINER = [re.compile(r'.r\d{2}$', re.I),
                           re.compile(r'.part\d+.rar$', re.I),
                           re.compile('.rar$', re.I)]
    COMPRESSEDCONTAINER += [re.compile('{0}$'.format(ext), re.I) for ext in CFG['Extensions']['compressedExtensions']]
    MEDIACONTAINER = CFG['Extensions']['mediaExtensions']
    AUDIOCONTAINER = CFG['Extensions']['audioExtensions']
    METACONTAINER = CFG['Extensions']['metaExtensions']  # .nfo,.sub,.srt
    if isinstance(COMPRESSEDCONTAINER, str):
        COMPRESSEDCONTAINER = COMPRESSEDCONTAINER.split(',')
    if isinstance(MEDIACONTAINER, str):
        MEDIACONTAINER = MEDIACONTAINER.split(',')
    if isinstance(AUDIOCONTAINER, str):
        AUDIOCONTAINER = AUDIOCONTAINER.split(',')
    if isinstance(METACONTAINER, str):
        METACONTAINER = METACONTAINER.split(',')

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
        'libfaac': ['libfaac', 'aac', 'faac']
    }
    transcode_defaults = {
        'iPad': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': None, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        },
        'iPad-1080p': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '1920:1080', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': None, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        },
        'iPad-720p': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '1280:720', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': None, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        },
        'Apple-TV': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '1280:720', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'ac3', 'ACODEC_ALLOW': ['ac3'], 'ABITRATE': None, 'ACHANNELS': 6,
            'ACODEC2': 'aac', 'ACODEC2_ALLOW': ['libfaac'], 'ABITRATE2': None, 'ACHANNELS2': 2,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        },
        'iPod': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '1280:720', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2,
            'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        },
        'iPhone': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '460:320', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2,
            'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        },
        'PS3': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'ac3', 'ACODEC_ALLOW': ['ac3'], 'ABITRATE': None, 'ACHANNELS': 6,
            'ACODEC2': 'aac', 'ACODEC2_ALLOW': ['libfaac'], 'ABITRATE2': None, 'ACHANNELS2': 2,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        },
        'xbox': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'ac3', 'ACODEC_ALLOW': ['ac3'], 'ABITRATE': None, 'ACHANNELS': 6,
            'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        },
        'Roku-480p': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        },
        'Roku-720p': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        },
        'Roku-1080p': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 160000, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        },
        'mkv': {
            'VEXTENSION': '.mkv', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4', 'mpeg2video'],
            'ACODEC': 'dts', 'ACODEC_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE': None, 'ACHANNELS': 8,
            'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None,
            'ACODEC3': 'ac3', 'ACODEC3_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE3': None, 'ACHANNELS3': 8,
            'SCODEC': 'mov_text'
        },
        'mp4-scene-release': {
            'VEXTENSION': '.mp4', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': None, 'VCRF': 19, 'VLEVEL': '3.1',
            'VRESOLUTION': None, 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4', 'mpeg2video'],
            'ACODEC': 'dts', 'ACODEC_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE': None, 'ACHANNELS': 8,
            'ACODEC2': None, 'ACODEC2_ALLOW': [], 'ABITRATE2': None, 'ACHANNELS2': None,
            'ACODEC3': 'ac3', 'ACODEC3_ALLOW': ['libfaac', 'dts', 'ac3', 'mp2', 'mp3'], 'ABITRATE3': None, 'ACHANNELS3': 8,
            'SCODEC': 'mov_text'
        },
        'MKV-SD': {
            'VEXTENSION': '.mkv', 'VCODEC': 'libx264', 'VPRESET': None, 'VFRAMERATE': None, 'VBITRATE': '1200k', 'VCRF': None, 'VLEVEL': None,
            'VRESOLUTION': '720: -1', 'VCODEC_ALLOW': ['libx264', 'h264', 'h.264', 'AVC', 'avc', 'mpeg4', 'msmpeg4', 'MPEG-4'],
            'ACODEC': 'aac', 'ACODEC_ALLOW': ['libfaac'], 'ABITRATE': 128000, 'ACHANNELS': 2,
            'ACODEC2': 'ac3', 'ACODEC2_ALLOW': ['ac3'], 'ABITRATE2': None, 'ACHANNELS2': 6,
            'ACODEC3': None, 'ACODEC3_ALLOW': [], 'ABITRATE3': None, 'ACHANNELS3': None,
            'SCODEC': 'mov_text'
        }
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

    PASSWORDSFILE = CFG['passwords']['PassWordFile']

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
        try:
            SEVENZIP = subprocess.Popen(['which', '7z'], stdout=subprocess.PIPE).communicate()[0].strip()
        except Exception:
            pass
        if not SEVENZIP:
            try:
                SEVENZIP = subprocess.Popen(['which', '7zr'], stdout=subprocess.PIPE).communicate()[0].strip()
            except Exception:
                pass
        if not SEVENZIP:
            try:
                SEVENZIP = subprocess.Popen(['which', '7za'], stdout=subprocess.PIPE).communicate()[0].strip()
            except Exception:
                pass
        if not SEVENZIP:
            SEVENZIP = None
            logger.warning(
                'Failed to locate 7zip. Transcoding of disk images and extraction of .7z files will not be possible!')
        try:
            PAR2CMD = subprocess.Popen(['which', 'par2'], stdout=subprocess.PIPE).communicate()[0].strip()
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
                FFMPEG = subprocess.Popen(['which', 'ffmpeg'], stdout=subprocess.PIPE).communicate()[0].strip()
            except Exception:
                pass
            if not FFMPEG:
                try:
                    FFMPEG = subprocess.Popen(['which', 'avconv'], stdout=subprocess.PIPE).communicate()[0].strip()
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
                FFPROBE = subprocess.Popen(['which', 'ffprobe'], stdout=subprocess.PIPE).communicate()[0].strip()
            except Exception:
                pass
            if not FFPROBE:
                try:
                    FFPROBE = subprocess.Popen(['which', 'avprobe'], stdout=subprocess.PIPE).communicate()[0].strip()
                except Exception:
                    pass
        if not FFPROBE:
            FFPROBE = None
            if CHECK_MEDIA:
                logger.warning('Failed to locate ffprobe. Video corruption detection disabled!')
                logger.warning('Install ffmpeg with x264 support to enable this feature  ...')

    # check for script-defied section and if None set to allow sections
    SECTIONS = CFG[tuple(x for x in CFG if CFG[x].sections and CFG[x].isenabled()) if not section else (section,)]
    for section, subsections in SECTIONS.items():
        CATEGORIES.extend([subsection for subsection in subsections if CFG[section][subsection].isenabled()])
    CATEGORIES = list(set(CATEGORIES))

    # create torrent class
    TORRENT_CLASS = create_torrent_class(TORRENT_CLIENTAGENT)

    # finished initalizing
    return True
