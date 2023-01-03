from __future__ import annotations

import itertools
import logging
import os
import pathlib
import re
import sys
import typing
from typing import Any

import setuptools_scm

import nzb2media.databases
import nzb2media.fork.medusa
import nzb2media.fork.sickbeard
import nzb2media.fork.sickchill
import nzb2media.fork.sickgear
import nzb2media.tool
from nzb2media.configuration import Config
from nzb2media.transcoder import configure_transcoder
from nzb2media.utils.network import wake_up

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

__version__ = setuptools_scm.get_version()


def module_path(module=__file__):
    try:
        path = pathlib.Path(module.__file__)
    except AttributeError:
        path = pathlib.Path(module)
    return path.parent.absolute()


APP_ROOT = module_path().parent
# init preliminaries
APP_NAME: str = pathlib.Path(sys.argv[0]).name
LOG_DIR: pathlib.Path = APP_ROOT / 'logs'
LOG_FILE: pathlib.Path = LOG_DIR / 'nzbtomedia.log'
PID_FILE = LOG_DIR / 'nzbtomedia.pid'
CONFIG_FILE = APP_ROOT / 'autoProcessMedia.cfg'
CONFIG_SPEC_FILE = APP_ROOT / 'autoProcessMedia.cfg.spec'
TEST_FILE = APP_ROOT / 'tests' / 'test.mp4'

FORKS: typing.Mapping[str, typing.Mapping[str, Any]] = {
    'default': {'dir': None},
    'failed': {'dirName': None, 'failed': None},
    'failed-torrent': {'dir': None, 'failed': None, 'process_method': None},
    **nzb2media.fork.sickbeard.CONFIG,
    **nzb2media.fork.sickchill.CONFIG,
    **nzb2media.fork.sickgear.CONFIG,
    **nzb2media.fork.medusa.CONFIG,
}
ALL_FORKS = {k: None for k in set(itertools.chain.from_iterable([FORKS[x].keys() for x in FORKS.keys()]))}
CFG = None
FAILED = False
FORCE_CLEAN = None
SAFE_MODE = None
NOEXTRACTFAILED = None
USE_LINK = None
OUTPUT_DIRECTORY = None
DELETE_ORIGINAL = None
REMOTE_PATHS = []
EXT_CONTAINER: list[str] = []
COMPRESSED_CONTAINER = []
MEDIA_CONTAINER = []
AUDIO_CONTAINER = []
META_CONTAINER = []
SECTIONS: list[str] = []
CATEGORIES: list[str] = []
FORK_SET: list[str] = []
SYS_PATH = None
CHECK_MEDIA = None
REQUIRE_LAN = None
PASSWORDS_FILE = None
DOWNLOAD_INFO = None
GROUPS = None
__INITIALIZED__ = False


def configure_migration():
    global CONFIG_FILE
    global CFG
    # run migrate to convert old cfg to new style cfg plus fix any cfg missing values/options.
    if not Config.migrate():
        log.error(f'Unable to migrate config file {CONFIG_FILE}, exiting ...')
        if 'NZBOP_SCRIPTDIR' in os.environ:
            pass  # We will try and read config from Environment.
        else:
            sys.exit(-1)
    # run migrate to convert NzbGet data from old cfg style to new cfg style
    if 'NZBOP_SCRIPTDIR' in os.environ:
        CFG = Config.addnzbget()
    else:  # load newly migrated config
        log.info(f'Loading config from [{CONFIG_FILE}]')
        CFG = Config(None)


def configure_general():
    global FORCE_CLEAN
    global SYS_PATH
    global CHECK_MEDIA
    global REQUIRE_LAN
    global SAFE_MODE
    global NOEXTRACTFAILED
    FORCE_CLEAN = int(CFG['General']['force_clean'])
    nzb2media.tool.FFMPEG_PATH = pathlib.Path(CFG['General']['ffmpeg_path'])
    SYS_PATH = CFG['General']['sys_path']
    CHECK_MEDIA = int(CFG['General']['check_media'])
    REQUIRE_LAN = None if not CFG['General']['require_lan'] else CFG['General']['require_lan'].split(',')
    SAFE_MODE = int(CFG['General']['safe_mode'])
    NOEXTRACTFAILED = int(CFG['General']['no_extract_failed'])


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
            # fix in case this imported as list.
            REMOTE_PATHS = ','.join(REMOTE_PATHS)
        # /volume1/Public/,E:\|/volume2/share/,\\NAS\
        REMOTE_PATHS = (tuple(item.split(',')) for item in REMOTE_PATHS.split('|'))
        # strip trailing and leading whitespaces
        REMOTE_PATHS = [(local.strip(), remote.strip()) for local, remote in REMOTE_PATHS]


def configure_containers():
    global COMPRESSED_CONTAINER
    global MEDIA_CONTAINER
    global AUDIO_CONTAINER
    global META_CONTAINER
    COMPRESSED_CONTAINER = [re.compile(r'.r\d{2}$', re.I), re.compile(r'.part\d+.rar$', re.I), re.compile('.rar$', re.I)]
    COMPRESSED_CONTAINER += [re.compile(f'{ext}$', re.I) for ext in CFG['Extensions']['compressedExtensions']]
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


def configure_passwords_file():
    global PASSWORDS_FILE
    PASSWORDS_FILE = CFG['passwords']['PassWordFile']


def configure_sections(section):
    global SECTIONS
    global CATEGORIES
    # check for script-defied SECTION and if None set to allow sections
    SECTIONS = CFG[tuple(x for x in CFG if CFG[x].sections and CFG[x].isenabled()) if not section else (section,)]
    for section, subsections in SECTIONS.items():
        CATEGORIES.extend([subsection for subsection in subsections if CFG[section][subsection].isenabled()])
    CATEGORIES = list(set(CATEGORIES))


def initialize(section=None):
    global __INITIALIZED__
    if __INITIALIZED__:
        return False
    configure_migration()
    # initialize the main SB database
    configure_general()
    configure_wake_on_lan()
    configure_remote_paths()
    nzb2media.tool.configure_niceness()
    configure_containers()
    configure_transcoder()
    configure_passwords_file()
    nzb2media.tool.configure_utility_locations()
    configure_sections(section)
    __INITIALIZED__ = True
    # finished initializing
    return __INITIALIZED__
