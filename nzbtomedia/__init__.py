import locale
import os
import re
import subprocess
import sys
import platform

# init libs
PROGRAM_DIR = os.path.dirname(os.path.normpath(os.path.abspath(os.path.join(__file__, os.pardir))))
LIBS_DIR = os.path.join(PROGRAM_DIR, 'libs')
sys.path.insert(0, LIBS_DIR)

# init preliminaries
SYS_ARGV = sys.argv[1:]
APP_FILENAME = sys.argv[0]
APP_NAME = os.path.basename(APP_FILENAME)
LOG_DIR = os.path.join(PROGRAM_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'postprocess.log')
CONFIG_FILE = os.path.join(PROGRAM_DIR, 'autoProcessMedia.cfg')
CONFIG_SPEC_FILE = os.path.join(PROGRAM_DIR, 'autoProcessMedia.cfg.spec')
CONFIG_MOVIE_FILE = os.path.join(PROGRAM_DIR, 'autoProcessMovie.cfg')
CONFIG_TV_FILE = os.path.join(PROGRAM_DIR, 'autoProcessTv.cfg')

from nzbtomedia.autoProcess.autoProcessComics import autoProcessComics
from nzbtomedia.autoProcess.autoProcessGames import autoProcessGames
from nzbtomedia.autoProcess.autoProcessMovie import autoProcessMovie
from nzbtomedia.autoProcess.autoProcessMusic import autoProcessMusic
from nzbtomedia.autoProcess.autoProcessTV import autoProcessTV
from nzbtomedia import logger, versionCheck, nzbToMediaDB
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaUtil import category_search, sanitizeName, copy_link, parse_args, flatten, getDirs, \
    rmReadOnly,rmDir, pause_torrent, resume_torrent, remove_torrent, listMediaFiles, \
    extractFiles, cleanDir, update_downloadInfoStatus, get_downloadInfo, WakeUp, makeDir, cleanDir, \
    create_torrent_class, listMediaFiles
from nzbtomedia.transcoder import transcoder
from nzbtomedia.databases import mainDB

# Client Agents
NZB_CLIENTS = ['sabnzbd','nzbget']
TORRENT_CLIENTS = ['transmission', 'deluge', 'utorrent']

# sabnzbd constants
SABNZB_NO_OF_ARGUMENTS = 8
SABNZB_0717_NO_OF_ARGUMENTS = 9

# sickbeard fork/branch constants
FORKS = {}
FORK_DEFAULT = "default"
FORK_FAILED = "failed"
FORK_FAILED_TORRENT = "failed-torrent"
FORKS[FORK_DEFAULT] = {"dir": None, "method": None}
FORKS[FORK_FAILED] = {"dirName": None, "failed": None}
FORKS[FORK_FAILED_TORRENT] = {"dir": None, "failed": None, "process_method": None}
SICKBEARD_FAILED = [FORK_FAILED, FORK_FAILED_TORRENT]
SICKBEARD_TORRENT = [FORK_FAILED_TORRENT]

# NZBGet Exit Codes
NZBGET_POSTPROCESS_PARCHECK = 92
NZBGET_POSTPROCESS_SUCCESS = 93
NZBGET_POSTPROCESS_ERROR = 94
NZBGET_POSTPROCESS_NONE = 95

CFG = None
LOG_DEBUG = None
LOG_DB = None
SYS_ENCODING = None

AUTO_UPDATE = None
NZBTOMEDIA_VERSION = None
NEWEST_VERSION = None
NEWEST_VERSION_STRING = None
VERSION_NOTIFY = None
GIT_PATH = None
GIT_USER = None
GIT_BRANCH = None
GIT_REPO = None
FORCE_CLEAN = None
SAFE_MODE = None

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
TORRENT_DEFAULTDIR = None

UTORRENTWEBUI = None
UTORRENTUSR = None
UTORRENTPWD = None

TRANSMISSIONHOST = None
TRANSMISSIONPORT = None
TRANSMISSIONUSR = None
TRANSMISSIONPWD = None

DELUGEHOST = None
DELUGEPORT = None
DELUGEUSR = None
DELUGEPWD = None

EXTCONTAINER = []
COMPRESSEDCONTAINER = []
EXT_REPLACE = {}
MEDIACONTAINER = []
AUDIOCONTAINER = []
METACONTAINER = []

SECTIONS = []
CATEGORIES = []
USER_SCRIPT_CATEGORIES = []

TRANSCODE = None
FFMPEG_PATH = None
DUPLICATE = None
IGNOREEXTENSIONS = None
OUTPUTVIDEOEXTENSION = None
OUTPUTVIDEOCODEC = None
OUTPUTVIDEOPRESET = None
OUTPUTVIDEOFRAMERATE = None
OUTPUTVIDEOBITRATE = None
OUTPUTAUDIOCODEC = None
OUTPUTAUDIOBITRATE = None
OUTPUTSUBTITLECODEC = None
OUTPUTFASTSTART = None
OUTPUTQUALITYPERCENT = None
FFMPEG = None
FFPROBE = None
CHECK_MEDIA = None
NICENESS = None

PASSWORDSFILE = None
DOWNLOADINFO = None

USER_SCRIPT_MEDIAEXTENSIONS = None
USER_SCRIPT = None
USER_SCRIPT_PARAM = None
USER_SCRIPT_SUCCESSCODES = None
USER_SCRIPT_CLEAN = None
USER_DELAY = None
USER_SCRIPT_RUNONCE = None

__INITIALIZED__ = False

def initialize(section=None):
    global NZBGET_POSTPROCESS_ERROR, NZBGET_POSTPROCESS_NONE, NZBGET_POSTPROCESS_PARCHECK, NZBGET_POSTPROCESS_SUCCESS, \
        NZBTOMEDIA_TIMEOUT, FORKS, FORK_DEFAULT, FORK_FAILED_TORRENT, FORK_FAILED, SICKBEARD_TORRENT, SICKBEARD_FAILED, \
        NZBTOMEDIA_BRANCH, NZBTOMEDIA_VERSION, NEWEST_VERSION, NEWEST_VERSION_STRING, VERSION_NOTIFY, SYS_ARGV, CFG, \
        SABNZB_NO_OF_ARGUMENTS, SABNZB_0717_NO_OF_ARGUMENTS, CATEGORIES, TORRENT_CLIENTAGENT, USELINK, OUTPUTDIRECTORY, NOFLATTEN, \
        UTORRENTPWD, UTORRENTUSR, UTORRENTWEBUI, DELUGEHOST, DELUGEPORT, DELUGEUSR, DELUGEPWD, TRANSMISSIONHOST, TRANSMISSIONPORT, \
        TRANSMISSIONPWD, TRANSMISSIONUSR, COMPRESSEDCONTAINER, MEDIACONTAINER, METACONTAINER, SECTIONS, USER_SCRIPT_CATEGORIES, \
        __INITIALIZED__, AUTO_UPDATE, APP_FILENAME, USER_DELAY, APP_NAME, TRANSCODE, GIT_PATH, GIT_USER, \
        GIT_BRANCH, GIT_REPO, SYS_ENCODING, NZB_CLIENTAGENT, SABNZBDHOST, SABNZBDPORT, SABNZBDAPIKEY, \
        DUPLICATE, IGNOREEXTENSIONS, OUTPUTVIDEOEXTENSION, OUTPUTVIDEOCODEC, OUTPUTVIDEOPRESET, OUTPUTVIDEOFRAMERATE, LOG_DB, \
        OUTPUTVIDEOBITRATE, OUTPUTAUDIOCODEC, OUTPUTAUDIOBITRATE, OUTPUTSUBTITLECODEC, OUTPUTFASTSTART, OUTPUTQUALITYPERCENT, \
        NICENESS, LOG_DEBUG, FORCE_CLEAN, FFMPEG_PATH, FFMPEG, FFPROBE, AUDIOCONTAINER, EXTCONTAINER, TORRENT_CLASS, \
        DELETE_ORIGINAL, PASSWORDSFILE, USER_DELAY, USER_SCRIPT, USER_SCRIPT_CLEAN, USER_SCRIPT_MEDIAEXTENSIONS, \
        USER_SCRIPT_PARAM, USER_SCRIPT_RUNONCE, USER_SCRIPT_SUCCESSCODES, DOWNLOADINFO, EXT_REPLACE, CHECK_MEDIA, SAFE_MODE, \
        TORRENT_DEFAULTDIR, NZB_DEFAULTDIR

    if __INITIALIZED__:
        return False

    try:
        locale.setlocale(locale.LC_ALL, "")
        SYS_ENCODING = locale.getpreferredencoding()
    except (locale.Error, IOError):
        pass

    # For OSes that are poorly configured I'll just randomly force UTF-8
    if not SYS_ENCODING or SYS_ENCODING in ('ANSI_X3.4-1968', 'US-ASCII', 'ASCII'):
        SYS_ENCODING = 'UTF-8'

    if not hasattr(sys, "setdefaultencoding"):
        reload(sys)

    try:
        # pylint: disable=E1101
        # On non-unicode builds this will raise an AttributeError, if encoding type is not valid it throws a LookupError
        sys.setdefaultencoding(SYS_ENCODING)
    except:
        print 'Sorry, you MUST add the nzbToMedia folder to the PYTHONPATH environment variable'
        print 'or find another way to force Python to use ' + SYS_ENCODING + ' for string encoding.'
        if os.environ.has_key('NZBOP_SCRIPTDIR'):
            sys.exit(NZBGET_POSTPROCESS_ERROR)
        else:
            sys.exit(1)

    if not makeDir(LOG_DIR):
        print("!!! No log folder, logging to screen only!")

    # init logging
    logger.ntm_log_instance.initLogging()

    # run migrate to convert old cfg to new style cfg plus fix any cfg missing values/options.
    if not config.migrate():
        logger.error("Unable to migrate config file %s, exiting ..." % (CONFIG_FILE))
        if os.environ.has_key('NZBOP_SCRIPTDIR'):
            pass  # We will try and read config from Environment.
        else:
            sys.exit(-1)

    # run migrate to convert NzbGet data from old cfg style to new cfg style
    if os.environ.has_key('NZBOP_SCRIPTDIR'):
        CFG = config.addnzbget()

    else:  # load newly migrated config
        logger.info("Loading config from [%s]" % (CONFIG_FILE))
        CFG = config()

    # Enable/Disable DEBUG Logging
    LOG_DEBUG = int(CFG['General']['log_debug'])
    LOG_DB = int(CFG['General']['log_db'])

    # initialize the main SB database
    nzbToMediaDB.upgradeDatabase(nzbToMediaDB.DBConnection(), mainDB.InitialSchema)

    # Set Version and GIT variables
    NZBTOMEDIA_VERSION = '9.3'
    VERSION_NOTIFY = int(CFG['General']['version_notify'])
    AUTO_UPDATE = int(CFG['General']['auto_update'])
    GIT_REPO = 'nzbToMedia'
    GIT_PATH = CFG['General']['git_path']
    GIT_USER = CFG['General']['git_user'] or 'clinton-hall'
    GIT_BRANCH = CFG['General']['git_branch'] or 'dev'
    FORCE_CLEAN = CFG["General"]["force_clean"]
    FFMPEG_PATH = CFG["General"]["ffmpeg_path"]
    CHECK_MEDIA = int(CFG["General"]["check_media"])
    SAFE_MODE = int(CFG["General"]["safe_mode"])

    # Check for updates via GitHUB
    if versionCheck.CheckVersion().check_for_new_version():
        if AUTO_UPDATE == 1:
            logger.info("Auto-Updating nzbToMedia, Please wait ...")
            updated = versionCheck.CheckVersion().update()
            if updated:
                # restart nzbToMedia
                restart()
            else:
                logger.error("Update wasn't successful, not restarting. Check your log for more information.")

    # Set Current Version
    logger.info(
        'nzbToMedia Version:' + NZBTOMEDIA_VERSION + ' Branch:' + GIT_BRANCH + ' (' + platform.system() + ' ' + platform.release() + ')')

    if int(CFG["WakeOnLan"]["wake"]) == 1:
        WakeUp()

    NZB_CLIENTAGENT = CFG["Nzb"]["clientAgent"]  # sabnzbd
    SABNZBDHOST = CFG["Nzb"]["sabnzbd_host"]
    SABNZBDPORT = int(CFG["Nzb"]["sabnzbd_port"])
    SABNZBDAPIKEY = CFG["Nzb"]["sabnzbd_apikey"]
    NZB_DEFAULTDIR = int(CFG["Nzb"]["default_downloadDirectory"])

    TORRENT_CLIENTAGENT = CFG["Torrent"]["clientAgent"]  # utorrent | deluge | transmission | rtorrent | other
    USELINK = CFG["Torrent"]["useLink"]  # no | hard | sym
    OUTPUTDIRECTORY = CFG["Torrent"]["outputDirectory"]  # /abs/path/to/complete/
    NZB_DEFAULTDIR = int(CFG["Torrent"]["default_downloadDirectory"])
    CATEGORIES = (CFG["Torrent"]["categories"])  # music,music_videos,pictures,software
    NOFLATTEN = (CFG["Torrent"]["noFlatten"])
    if isinstance(NOFLATTEN, str): NOFLATTEN = NOFLATTEN.split(',')
    DELETE_ORIGINAL = int(CFG["Torrent"]["deleteOriginal"])
    UTORRENTWEBUI = CFG["Torrent"]["uTorrentWEBui"]  # http://localhost:8090/gui/
    UTORRENTUSR = CFG["Torrent"]["uTorrentUSR"]  # mysecretusr
    UTORRENTPWD = CFG["Torrent"]["uTorrentPWD"]  # mysecretpwr

    TRANSMISSIONHOST = CFG["Torrent"]["TransmissionHost"]  # localhost
    TRANSMISSIONPORT = int(CFG["Torrent"]["TransmissionPort"])
    TRANSMISSIONUSR = CFG["Torrent"]["TransmissionUSR"]  # mysecretusr
    TRANSMISSIONPWD = CFG["Torrent"]["TransmissionPWD"]  # mysecretpwr

    DELUGEHOST = CFG["Torrent"]["DelugeHost"]  # localhost
    DELUGEPORT = int(CFG["Torrent"]["DelugePort"])  # 8084
    DELUGEUSR = CFG["Torrent"]["DelugeUSR"]  # mysecretusr
    DELUGEPWD = CFG["Torrent"]["DelugePWD"]  # mysecretpwr

    COMPRESSEDCONTAINER = [re.compile('.r\d{2}$', re.I),
                  re.compile('.part\d+.rar$', re.I),
                  re.compile('.rar$', re.I)]
    COMPRESSEDCONTAINER += [re.compile('%s$' % ext, re.I) for ext in CFG["Extensions"]["compressedExtensions"]]
    EXT_REPLACE = {'.cbr':'.rar', '.cbz':'.zip'}  # extensions used for comic books need to be replaced before we can extract.
    MEDIACONTAINER = CFG["Extensions"]["mediaExtensions"]
    AUDIOCONTAINER = CFG["Extensions"]["audioExtensions"]
    METACONTAINER = CFG["Extensions"]["metaExtensions"]  # .nfo,.sub,.srt
    if isinstance(COMPRESSEDCONTAINER, str): COMPRESSEDCONTAINER = COMPRESSEDCONTAINER.split(',')
    if isinstance(MEDIACONTAINER, str): MEDIACONTAINER = MEDIACONTAINER.split(',')
    if isinstance(AUDIOCONTAINER, str): AUDIOCONTAINER = AUDIOCONTAINER.split(',')
    if isinstance(METACONTAINER, str): METACONTAINER = METACONTAINER.split(',')

    TRANSCODE = int(CFG["Transcoder"]["transcode"])
    DUPLICATE = int(CFG["Transcoder"]["duplicate"])
    IGNOREEXTENSIONS = (CFG["Transcoder"]["ignoreExtensions"])
    OUTPUTVIDEOEXTENSION = CFG["Transcoder"]["outputVideoExtension"].strip()
    OUTPUTVIDEOCODEC = CFG["Transcoder"]["outputVideoCodec"].strip()
    OUTPUTVIDEOPRESET = CFG["Transcoder"]["outputVideoPreset"].strip()
    OUTPUTVIDEOFRAMERATE = CFG["Transcoder"]["outputVideoFramerate"].strip()
    OUTPUTVIDEOBITRATE = CFG["Transcoder"]["outputVideoBitrate"].strip()
    OUTPUTAUDIOCODEC = CFG["Transcoder"]["outputAudioCodec"].strip()
    OUTPUTAUDIOBITRATE = CFG["Transcoder"]["outputAudioBitrate"].strip()
    OUTPUTSUBTITLECODEC = CFG["Transcoder"]["outputSubtitleCodec"].strip()
    OUTPUTFASTSTART = int(CFG["Transcoder"]["outputFastStart"])
    OUTPUTQUALITYPERCENT = int(CFG["Transcoder"]["outputQualityPercent"])
    NICENESS = int(CFG["Transcoder"]["niceness"])

    PASSWORDSFILE = CFG["passwords"]["PassWordFile"]

    # Setup FFMPEG and FFPROBE locations
    if platform.system() == 'Windows':
        FFMPEG = os.path.join(FFMPEG_PATH, 'ffmpeg.exe')
        FFPROBE = os.path.join(FFMPEG_PATH, 'ffprobe.exe')

        if not (os.path.isfile(FFMPEG)):  # problem
            FFMPEG = None
            logger.warning("Failed to locate ffmpeg.exe, transcoding disabled!")
            logger.warning("Install ffmpeg with x264 support to enable this feature  ...")

        if not (os.path.isfile(FFPROBE)) and CHECK_MEDIA:  # problem
            FFPROBE = None
            logger.warning("Failed to locate ffprobe.exe, video corruption detection disabled!")
            logger.warning("Install ffmpeg with x264 support to enable this feature  ...")

    else:
        FFMPEG = subprocess.Popen(['which', 'ffmpeg'], stdout=subprocess.PIPE).communicate()[0].strip()
        FFPROBE = subprocess.Popen(['which', 'ffprobe'], stdout=subprocess.PIPE).communicate()[0].strip()

        if not FFMPEG:
            if os.access(os.path.join(FFMPEG_PATH, 'ffmpeg'), os.X_OK):
                FFMPEG = os.path.join(FFMPEG_PATH, 'ffmpeg')
            else:
                FFMPEG = None
                logger.warning("Failed to locate ffmpeg, transcoding disabled!")
                logger.warning("Install ffmpeg with x264 support to enable this feature  ...")

        if not FFPROBE and CHECK_MEDIA:
            if os.access(os.path.join(FFMPEG_PATH, 'ffprobe'), os.X_OK):
                FFPROBE = os.path.join(FFMPEG_PATH, 'ffprobe')
            else:
                FFPROBE = None
                logger.warning("Failed to locate ffprobe, video corruption detection disabled!")
                logger.warning("Install ffmpeg with x264 support to enable this feature  ...")

    if not CHECK_MEDIA:  # allow users to bypass this.
        FFPROBE = None

    # userscript
    map(USER_SCRIPT_CATEGORIES.append, ([subsections[0] for subsections in CFG['UserScript'].items()]))

    # check for script-defied section and if None set to allow sections
    SECTIONS = CFG[tuple(x for x in CFG if CFG[x].sections and CFG[x].isenabled()) if not section else (section,)]
    map(CATEGORIES.extend,([subsection.sections for section,subsection in SECTIONS.items()]))
    CATEGORIES = list(set(CATEGORIES))

    # create torrent class
    TORRENT_CLASS = create_torrent_class(TORRENT_CLIENTAGENT)

    # finished initalizing
    return True

def restart():
    install_type = versionCheck.CheckVersion().install_type

    status = 0
    popen_list = []

    if install_type in ('git', 'source'):
        popen_list = [sys.executable, APP_FILENAME]

    if popen_list:
        popen_list += SYS_ARGV
        logger.log(u"Restarting nzbToMedia with " + str(popen_list))
        logger.close()
        p = subprocess.Popen(popen_list, cwd=os.getcwd())
        p.wait()
        status = p.returncode

    os._exit(status)
