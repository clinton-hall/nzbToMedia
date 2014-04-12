import os
import subprocess
import sys
import platform
from nzbtomedia import logger, versionCheck
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaUtil import WakeUp

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

# config constants
CFG = None
CFG_LOGGING = None
PROGRAM_DIR = ''
LOG_DIR = ''
LOG_FILE = ''
CONFIG_FILE = ''
CONFIG_SPEC_FILE = ''
CONFIG_MOVIE_FILE = ''
CONFIG_TV_FILE = ''
SYS_ENCODING = ''
SYSV_ARGS = ''

# version constants
AUTO_UPDATE = None
NZBTOMEDIA_VERSION = None
NZBTOMEDIA_BRANCH = None
NEWEST_VERSION = None
NEWEST_VERSION_STRING = None
VERSION_NOTIFY = None

GIT_PATH = None
GIT_USER = None
GIT_BRANCH = None

CLIENTAGENT = None
USELINK = None
OUTPUTDIRECTORY = None
CATEGORIES = []
NOFLATTEN = []

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

COMPRESSEDCONTAINER = None
MEDIACONTAINER = None
METACONTAINER = None
MINSAMPLESIZE = None
SAMPLEIDS = None

SECTIONS = []
SUBSECTIONS = {}

USER_SCRIPT_CATEGORIES = None

__INITIALIZED__ = False

def initialize():
    global NZBGET_POSTPROCESS_ERROR, NZBGET_POSTPROCESS_NONE, NZBGET_POSTPROCESS_PARCHECK, NZBGET_POSTPROCESS_SUCCESS, \
        NZBTOMEDIA_TIMEOUT, FORKS, FORK_DEFAULT, FORK_FAILED_TORRENT, FORK_FAILED, SICKBEARD_TORRENT, SICKBEARD_FAILED, \
        PROGRAM_DIR, CFG, CFG_LOGGING, CONFIG_FILE, CONFIG_MOVIE_FILE, CONFIG_SPEC_FILE, LOG_DIR, NZBTOMEDIA_BRANCH, \
        CONFIG_TV_FILE, LOG_FILE, NZBTOMEDIA_VERSION, NEWEST_VERSION, NEWEST_VERSION_STRING, VERSION_NOTIFY, SYSV_ARGS, \
        SABNZB_NO_OF_ARGUMENTS, SABNZB_0717_NO_OF_ARGUMENTS, CATEGORIES, CLIENTAGENT, USELINK, OUTPUTDIRECTORY, NOFLATTEN, \
        UTORRENTPWD, UTORRENTUSR, UTORRENTWEBUI, DELUGEHOST, DELUGEPORT, DELUGEUSR, DELUGEPWD, TRANSMISSIONHOST, TRANSMISSIONPORT, \
        TRANSMISSIONPWD, TRANSMISSIONUSR, COMPRESSEDCONTAINER, MEDIACONTAINER, METACONTAINER, MINSAMPLESIZE, SAMPLEIDS, \
        SECTIONS, SUBSECTIONS, USER_SCRIPT_CATEGORIES, __INITIALIZED__, GIT_PATH, GIT_USER, GIT_BRANCH, AUTO_UPDATE

    if __INITIALIZED__:
        return False

    # add our custom libs to the system path
    sys.path.insert(0, os.path.abspath(os.path.join(PROGRAM_DIR, 'lib')))

    # init preliminaries
    PROGRAM_DIR = os.path.dirname(os.path.normpath(os.path.abspath(os.path.join(__file__, os.pardir))))
    LOG_DIR = os.path.join(PROGRAM_DIR, 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'postprocess.log')
    CONFIG_FILE = os.path.join(PROGRAM_DIR, "autoProcessMedia.cfg")
    CONFIG_SPEC_FILE = os.path.join(PROGRAM_DIR, "autoProcessMedia.cfg.spec")
    CONFIG_MOVIE_FILE = os.path.join(PROGRAM_DIR, "autoProcessMovie.cfg")
    CONFIG_TV_FILE = os.path.join(PROGRAM_DIR, "autoProcessTv.cfg")
    SYSV_ARGS = sys.argv[1:]

    if not nzbToMediaUtil.makeDir(LOG_DIR):
        logger.error("!!! No log folder, logging to screen only!")

    # init logging
    logger.ntm_log_instance.initLogging()

    # run migrate to convert old cfg to new style cfg plus fix any cfg missing values/options.
    if not config.migrate():
        logger.error("Unable to load config from %s", CONFIG_FILE)
        sys.exit(-1)

    if os.environ.has_key('NZBOP_SCRIPTDIR'):
        config.addnzbget()

    # load newly migrated config
    logger.info("Loading config from %s", CONFIG_FILE)
    CFG = config()

    # check for newer version
    versionCheck.CheckVersion().find_installed_version()
    logger.info('nzbToMedia Version:' + NZBTOMEDIA_VERSION + ' Branch:' + NZBTOMEDIA_BRANCH + ' (' + platform.system() + '; ' + platform.release() + ')')
    if CFG['General']['auto_update'] == 1 and versionCheck.CheckVersion().check_for_new_version():
        logger.MESSAGE("Auto-Updating nzbToMedia, Please wait ...")
        updated = versionCheck.CheckVersion().update()
        if updated:
            # restart nzbToMedia
            restart()
        else:
            logger.ERROR("Update wasn't successful, not restarting. Check your log for more information.")

    WakeUp()

    CLIENTAGENT = CFG["Torrent"]["clientAgent"]  # utorrent | deluge | transmission | rtorrent | other
    USELINK = CFG["Torrent"]["useLink"]  # no | hard | sym
    OUTPUTDIRECTORY = CFG["Torrent"]["outputDirectory"]  # /abs/path/to/complete/
    CATEGORIES = (CFG["Torrent"]["categories"])  # music,music_videos,pictures,software
    NOFLATTEN = (CFG["Torrent"]["noFlatten"])

    UTORRENTWEBUI = CFG["Torrent"]["uTorrentWEBui"]  # http://localhost:8090/gui/
    UTORRENTUSR = CFG["Torrent"]["uTorrentUSR"]  # mysecretusr
    UTORRENTPWD = CFG["Torrent"]["uTorrentPWD"]  # mysecretpwr

    TRANSMISSIONHOST = CFG["Torrent"]["TransmissionHost"]  # localhost
    TRANSMISSIONPORT = CFG["Torrent"]["TransmissionPort"]  # 8084
    TRANSMISSIONUSR = CFG["Torrent"]["TransmissionUSR"]  # mysecretusr
    TRANSMISSIONPWD = CFG["Torrent"]["TransmissionPWD"]  # mysecretpwr

    DELUGEHOST = CFG["Torrent"]["DelugeHost"]  # localhost
    DELUGEPORT = CFG["Torrent"]["DelugePort"]  # 8084
    DELUGEUSR = CFG["Torrent"]["DelugeUSR"]  # mysecretusr
    DELUGEPWD = CFG["Torrent"]["DelugePWD"]  # mysecretpwr

    COMPRESSEDCONTAINER = (CFG["Extensions"]["compressedExtensions"])  # .zip,.rar,.7z
    MEDIACONTAINER = (CFG["Extensions"]["mediaExtensions"])  # .mkv,.avi,.divx
    METACONTAINER = (CFG["Extensions"]["metaExtensions"])  # .nfo,.sub,.srt
    MINSAMPLESIZE = int(CFG["Extensions"]["minSampleSize"])  # 200 (in MB)
    SAMPLEIDS = (CFG["Extensions"]["SampleIDs"])  # sample,-s.

    SECTIONS = ("CouchPotato", "SickBeard", "NzbDrone", "HeadPhones", "Mylar", "Gamez")
    SUBSECTIONS = CFG[SECTIONS]
    CATEGORIES += SUBSECTIONS.sections

    USER_SCRIPT_CATEGORIES = CFG["UserScript"]["user_script_categories"]  # NONE

    GIT_PATH = CFG["General"]["git_path"]

    __INITIALIZED__ = True
    return True

def restart():
    install_type = versionCheck.CheckVersion().install_type

    popen_list = []

    if install_type in ('git', 'source'):
        popen_list = [sys.executable, PROGRAM_DIR]

    if popen_list:
        popen_list += SYSV_ARGS
        logger.log(u"Restarting nzbToMedia with " + str(popen_list))
        logger.close()
        subprocess.Popen(popen_list, cwd=os.getcwd())

    os._exit(0)
