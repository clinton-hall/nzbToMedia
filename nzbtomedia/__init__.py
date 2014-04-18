import locale
import os
import subprocess
import sys
import platform
from nzbtomedia import logger, versionCheck
from nzbtomedia.nzbToMediaConfig import config
from nzbtomedia.nzbToMediaUtil import WakeUp, makeDir

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
APP_FILENAME = ''
APP_NAME = ''
PROGRAM_DIR = ''
LOG_DIR = ''
LOG_FILE = ''
CONFIG_FILE = ''
CONFIG_SPEC_FILE = ''
CONFIG_MOVIE_FILE = ''
CONFIG_TV_FILE = ''
SYS_ENCODING = None
SYS_ARGV = None

# version constants
AUTO_UPDATE = None
NZBTOMEDIA_VERSION = None
NEWEST_VERSION = None
NEWEST_VERSION_STRING = None
VERSION_NOTIFY = None

GIT_PATH = None
GIT_USER = None
GIT_BRANCH = None
GIT_REPO = None

NZB_CLIENTAGENT = None
SABNZBDHOST = None
SABNZBDPORT = None
SABNZBDAPIKEY = None

TORRENT_CLIENTAGENT = None
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

TRANSCODE = None

USER_SCRIPT_CATEGORIES = None
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
        PROGRAM_DIR, CFG, CFG_LOGGING, CONFIG_FILE, CONFIG_MOVIE_FILE, CONFIG_SPEC_FILE, LOG_DIR, NZBTOMEDIA_BRANCH, \
        CONFIG_TV_FILE, LOG_FILE, NZBTOMEDIA_VERSION, NEWEST_VERSION, NEWEST_VERSION_STRING, VERSION_NOTIFY, SYS_ARGV, \
        SABNZB_NO_OF_ARGUMENTS, SABNZB_0717_NO_OF_ARGUMENTS, CATEGORIES, TORRENT_CLIENTAGENT, USELINK, OUTPUTDIRECTORY, NOFLATTEN, \
        UTORRENTPWD, UTORRENTUSR, UTORRENTWEBUI, DELUGEHOST, DELUGEPORT, DELUGEUSR, DELUGEPWD, TRANSMISSIONHOST, TRANSMISSIONPORT, \
        TRANSMISSIONPWD, TRANSMISSIONUSR, COMPRESSEDCONTAINER, MEDIACONTAINER, METACONTAINER, MINSAMPLESIZE, SAMPLEIDS, \
        SECTIONS, SUBSECTIONS, USER_SCRIPT_CATEGORIES, __INITIALIZED__, AUTO_UPDATE, APP_FILENAME, USER_DELAY, USER_SCRIPT_RUNONCE, \
        APP_NAME,USER_SCRIPT_MEDIAEXTENSIONS, USER_SCRIPT, USER_SCRIPT_PARAM, USER_SCRIPT_SUCCESSCODES, USER_SCRIPT_CLEAN, \
        TRANSCODE, GIT_PATH, GIT_USER, GIT_BRANCH, GIT_REPO, SYS_ENCODING, NZB_CLIENTAGENT, SABNZBDHOST, SABNZBDPORT, SABNZBDAPIKEY


    if __INITIALIZED__:
        return False

    # add our custom libs to the system path
    sys.path.insert(0, os.path.abspath(os.path.join(PROGRAM_DIR, 'lib')))

    # init preliminaries
    SYS_ARGV = sys.argv[1:]
    APP_FILENAME = sys.argv[0]
    APP_NAME = os.path.basename(APP_FILENAME)
    PROGRAM_DIR = os.path.dirname(os.path.normpath(os.path.abspath(os.path.join(__file__, os.pardir))))
    LOG_DIR = os.path.join(PROGRAM_DIR, 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'postprocess.log')
    CONFIG_FILE = os.path.join(PROGRAM_DIR, "autoProcessMedia.cfg")
    CONFIG_SPEC_FILE = os.path.join(PROGRAM_DIR, "autoProcessMedia.cfg.spec")
    CONFIG_MOVIE_FILE = os.path.join(PROGRAM_DIR, "autoProcessMovie.cfg")
    CONFIG_TV_FILE = os.path.join(PROGRAM_DIR, "autoProcessTv.cfg")

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
        sys.exit(1)

    if not makeDir(LOG_DIR):
        print("!!! No log folder, logging to screen only!")

    # init logging
    logger.ntm_log_instance.initLogging()

    # run migrate to convert old cfg to new style cfg plus fix any cfg missing values/options.
    if not config.migrate():
        logger.error("Unable to migrate config file %s, exiting ...", CONFIG_FILE)
        sys.exit(-1)

    # run migrate to convert NzbGet data from old cfg style to new cfg style
    if os.environ.has_key('NZBOP_SCRIPTDIR'):
        if not config.addnzbget():
            logger.error("Unable to migrate NzbGet config file %s, exiting ...", CONFIG_FILE)
            sys.exit(-1)

    # load newly migrated config
    logger.info("Loading config from %s", CONFIG_FILE)
    CFG = config()

    # Set Version and GIT variables
    NZBTOMEDIA_VERSION = '9.3'
    VERSION_NOTIFY = int(CFG['General']['version_notify'])
    AUTO_UPDATE = int(CFG['General']['auto_update'])
    GIT_PATH = CFG['General']['git_path']
    GIT_USER = CFG['General']['git_user'] or 'clinton-hall'
    GIT_BRANCH = CFG['General']['git_branch'] or 'dev'
    GIT_REPO = 'nzbToMedia'

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
    logger.info('nzbToMedia Version:' + NZBTOMEDIA_VERSION + ' Branch:' + GIT_BRANCH + ' (' + platform.system() + ' ' + platform.release() + ')')

    WakeUp()

    NZB_CLIENTAGENT = CFG["Nzb"]["clientAgent"]  # sabnzbd
    SABNZBDHOST = CFG["Nzb"]["sabnzbd_host"]
    SABNZBDPORT = int(CFG["Nzb"]["sabnzbd_port"])
    SABNZBDAPIKEY = CFG["Nzb"]["sabnzbd_apikey"]

    TORRENT_CLIENTAGENT = CFG["Torrent"]["clientAgent"]  # utorrent | deluge | transmission | rtorrent | other
    USELINK = CFG["Torrent"]["useLink"]  # no | hard | sym
    OUTPUTDIRECTORY = CFG["Torrent"]["outputDirectory"]  # /abs/path/to/complete/
    CATEGORIES = (CFG["Torrent"]["categories"])  # music,music_videos,pictures,software
    NOFLATTEN = (CFG["Torrent"]["noFlatten"])

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

    COMPRESSEDCONTAINER = (CFG["Extensions"]["compressedExtensions"])  # .zip,.rar,.7z
    MEDIACONTAINER = (CFG["Extensions"]["mediaExtensions"])  # .mkv,.avi,.divx
    METACONTAINER = (CFG["Extensions"]["metaExtensions"])  # .nfo,.sub,.srt
    MINSAMPLESIZE = int(CFG["Extensions"]["minSampleSize"])  # 200 (in MB)
    SAMPLEIDS = (CFG["Extensions"]["SampleIDs"])  # sample,-s.
    TRANSCODE = int(CFG["Transcoder"]["transcode"])

    # check for script-defied section and if None set to allow sections
    SECTIONS = ("CouchPotato", "SickBeard", "NzbDrone", "HeadPhones", "Mylar", "Gamez")
    if section:
        SECTIONS = (section,)

    SUBSECTIONS = CFG[SECTIONS]
    CATEGORIES += SUBSECTIONS.sections

    USER_SCRIPT_CATEGORIES = CFG["UserScript"]["user_script_categories"]
    if not "NONE" in USER_SCRIPT_CATEGORIES:
        USER_SCRIPT_MEDIAEXTENSIONS = (CFG["UserScript"]["user_script_mediaExtensions"])
        USER_SCRIPT = CFG["UserScript"]["user_script_path"]
        USER_SCRIPT_PARAM = (CFG["UserScript"]["user_script_param"])
        USER_SCRIPT_SUCCESSCODES = (CFG["UserScript"]["user_script_successCodes"])
        USER_SCRIPT_CLEAN = int(CFG["UserScript"]["user_script_clean"])
        USER_DELAY = int(CFG["UserScript"]["delay"])
        USER_SCRIPT_RUNONCE = int(CFG["UserScript"]["user_script_runOnce"])

    __INITIALIZED__ = True
    return True

def restart():
    install_type = versionCheck.CheckVersion().install_type

    popen_list = []

    if install_type in ('git', 'source'):
        popen_list = [sys.executable, APP_FILENAME]

    if popen_list:
        popen_list += SYS_ARGV
        logger.log(u"Restarting nzbToMedia with " + str(popen_list))
        logger.close()
        p = subprocess.Popen(popen_list, cwd=os.getcwd())
        p.wait()

    os._exit(0)
