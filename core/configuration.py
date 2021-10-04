# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import copy
import os
import shutil
from itertools import chain

import configobj
from six import iteritems

import core
from core import logger


class Section(configobj.Section, object):
    def isenabled(self):
        # checks if subsection enabled, returns true/false if subsection specified otherwise returns true/false in {}
        if not self.sections:
            try:
                value = list(ConfigObj.find_key(self, 'enabled'))[0]
            except Exception:
                value = 0
            if int(value) == 1:
                return self
        else:
            to_return = copy.deepcopy(self)
            for section_name, subsections in to_return.items():
                for subsection in subsections:
                    try:
                        value = list(ConfigObj.find_key(subsections, 'enabled'))[0]
                    except Exception:
                        value = 0

                    if int(value) != 1:
                        del to_return[section_name][subsection]

            # cleanout empty sections and subsections
            for key in [k for (k, v) in to_return.items() if not v]:
                del to_return[key]

            return to_return

    def findsection(self, key):
        to_return = copy.deepcopy(self)
        for subsection in to_return:
            try:
                value = list(ConfigObj.find_key(to_return[subsection], key))[0]
            except Exception:
                value = None

            if not value:
                del to_return[subsection]
            else:
                for category in to_return[subsection]:
                    if category != key:
                        del to_return[subsection][category]

        # cleanout empty sections and subsections
        for key in [k for (k, v) in to_return.items() if not v]:
            del to_return[key]

        return to_return

    def __getitem__(self, key):
        if key in self.keys():
            return dict.__getitem__(self, key)

        to_return = copy.deepcopy(self)
        for section, subsections in to_return.items():
            if section in key:
                continue
            if isinstance(subsections, Section) and subsections.sections:
                for subsection, options in subsections.items():
                    if subsection in key:
                        continue
                    if key in options:
                        return options[key]

                    del subsections[subsection]
            else:
                if section not in key:
                    del to_return[section]

        # cleanout empty sections and subsections
        for key in [k for (k, v) in to_return.items() if not v]:
            del to_return[key]

        return to_return


class ConfigObj(configobj.ConfigObj, Section):
    def __init__(self, *args, **kw):
        if len(args) == 0:
            args = (core.CONFIG_FILE,)
        super(configobj.ConfigObj, self).__init__(*args, **kw)
        self.interpolation = False

    @staticmethod
    def find_key(node, kv):
        if isinstance(node, list):
            for i in node:
                for x in ConfigObj.find_key(i, kv):
                    yield x
        elif isinstance(node, dict):
            if kv in node:
                yield node[kv]
            for j in node.values():
                for x in ConfigObj.find_key(j, kv):
                    yield x

    @staticmethod
    def migrate():
        global CFG_NEW, CFG_OLD
        CFG_NEW = None
        CFG_OLD = None

        try:
            # check for autoProcessMedia.cfg and create if it does not exist
            if not os.path.isfile(core.CONFIG_FILE):
                shutil.copyfile(core.CONFIG_SPEC_FILE, core.CONFIG_FILE)
            CFG_OLD = config(core.CONFIG_FILE)
        except Exception as error:
            logger.error('Error {msg} when copying to .cfg'.format(msg=error))

        try:
            # check for autoProcessMedia.cfg.spec and create if it does not exist
            if not os.path.isfile(core.CONFIG_SPEC_FILE):
                shutil.copyfile(core.CONFIG_FILE, core.CONFIG_SPEC_FILE)
            CFG_NEW = config(core.CONFIG_SPEC_FILE)
        except Exception as error:
            logger.error('Error {msg} when copying to .spec'.format(msg=error))

        # check for autoProcessMedia.cfg and autoProcessMedia.cfg.spec and if they don't exist return and fail
        if CFG_NEW is None or CFG_OLD is None:
            return False

        subsections = {}
        # gather all new-style and old-style sub-sections
        for newsection in CFG_NEW:
            if CFG_NEW[newsection].sections:
                subsections.update({newsection: CFG_NEW[newsection].sections})

        for section in CFG_OLD:
            if CFG_OLD[section].sections:
                subsections.update({section: CFG_OLD[section].sections})
            for option, value in CFG_OLD[section].items():
                if option in ['category',
                              'cpsCategory',
                              'sbCategory',
                              'srCategory',
                              'hpCategory',
                              'mlCategory',
                              'gzCategory',
                              'raCategory',
                              'ndCategory',
                              'W3Category']:
                    if not isinstance(value, list):
                        value = [value]

                    # add subsection
                    subsections.update({section: value})
                    CFG_OLD[section].pop(option)
                    continue

        def cleanup_values(values, section):
            for option, value in iteritems(values):
                if section in ['CouchPotato']:
                    if option == ['outputDirectory']:
                        CFG_NEW['Torrent'][option] = os.path.split(os.path.normpath(value))[0]
                        values.pop(option)
                if section in ['CouchPotato', 'HeadPhones', 'Gamez', 'Mylar']:
                    if option in ['username', 'password']:
                        values.pop(option)
                if section in ['Mylar']:
                    if option == 'wait_for':  # remove old format
                        values.pop(option)
                if section in ['SickBeard', 'NzbDrone']:
                    if option == 'failed_fork':  # change this old format
                        values['failed'] = 'auto'
                        values.pop(option)
                    if option == 'outputDirectory':  # move this to new location format
                        CFG_NEW['Torrent'][option] = os.path.split(os.path.normpath(value))[0]
                        values.pop(option)
                if section in ['Torrent']:
                    if option in ['compressedExtensions', 'mediaExtensions', 'metaExtensions', 'minSampleSize']:
                        CFG_NEW['Extensions'][option] = value
                        values.pop(option)
                    if option == 'useLink':  # Sym links supported now as well.
                        if value in ['1', 1]:
                            value = 'hard'
                        elif value in ['0', 0]:
                            value = 'no'
                        values[option] = value
                    if option == 'forceClean':
                        CFG_NEW['General']['force_clean'] = value
                        values.pop(option)
                    if option == 'qBittorrenHost':  # We had a typo that is now fixed.
                        CFG_NEW['Torrent']['qBittorrentHost'] = value
                        values.pop(option)
                if section in ['Transcoder']:
                    if option in ['niceness']:
                        CFG_NEW['Posix'][option] = value
                        values.pop(option)
                if option == 'remote_path':
                    if value and value not in ['0', '1', 0, 1]:
                        value = 1
                    elif not value:
                        value = 0
                    values[option] = value

                # remove any options that we no longer need so they don't migrate into our new config
                if not list(ConfigObj.find_key(CFG_NEW, option)):
                    try:
                        values.pop(option)
                    except Exception:
                        pass

            return values

        def process_section(section, subsections=None):
            if subsections:
                for subsection in subsections:
                    if subsection in CFG_OLD.sections:
                        values = cleanup_values(CFG_OLD[subsection], section)
                        if subsection not in CFG_NEW[section].sections:
                            CFG_NEW[section][subsection] = {}
                        for option, value in values.items():
                            CFG_NEW[section][subsection][option] = value
                    elif subsection in CFG_OLD[section].sections:
                        values = cleanup_values(CFG_OLD[section][subsection], section)
                        if subsection not in CFG_NEW[section].sections:
                            CFG_NEW[section][subsection] = {}
                        for option, value in values.items():
                            CFG_NEW[section][subsection][option] = value
            else:
                values = cleanup_values(CFG_OLD[section], section)
                if section not in CFG_NEW.sections:
                    CFG_NEW[section] = {}
                for option, value in values.items():
                    CFG_NEW[section][option] = value

        # convert old-style categories to new-style sub-sections
        for section in CFG_OLD.keys():
            subsection = None
            if section in list(chain.from_iterable(subsections.values())):
                subsection = section
                section = ''.join([k for k, v in iteritems(subsections) if subsection in v])
                process_section(section, subsection)
            elif section in subsections.keys():
                subsection = subsections[section]
                process_section(section, subsection)
            elif section in CFG_OLD.keys():
                process_section(section, subsection)

        # migrate SiCRKAGE settings from SickBeard section to new dedicated SiCRKAGE section
        if CFG_OLD['SickBeard']['tv']['enabled'] and CFG_OLD['SickBeard']['tv']['fork'] == 'sickrage-api':
            for option, value in iteritems(CFG_OLD['SickBeard']['tv']):
                if option in CFG_NEW['SiCKRAGE']['tv']:
                    CFG_NEW['SiCKRAGE']['tv'][option] = value

            # set API version to 1 if API key detected and no SSO username is set
            if CFG_NEW['SiCKRAGE']['tv']['apikey'] and not CFG_NEW['SiCKRAGE']['tv']['sso_username']:
                CFG_NEW['SiCKRAGE']['tv']['api_version'] = 1

            # disable SickBeard section
            CFG_NEW['SickBeard']['tv']['enabled'] = 0
            CFG_NEW['SickBeard']['tv']['fork'] = 'auto'

        # create a backup of our old config
        CFG_OLD.filename = '{config}.old'.format(config=core.CONFIG_FILE)
        CFG_OLD.write()

        # write our new config to autoProcessMedia.cfg
        CFG_NEW.filename = core.CONFIG_FILE
        CFG_NEW.write()

        return True

    @staticmethod
    def addnzbget():
        # load configs into memory
        cfg_new = config()

        try:
            if 'NZBPO_NDCATEGORY' in os.environ and 'NZBPO_SBCATEGORY' in os.environ:
                if os.environ['NZBPO_NDCATEGORY'] == os.environ['NZBPO_SBCATEGORY']:
                    logger.warning('{x} category is set for SickBeard and Sonarr. '
                                   'Please check your config in NZBGet'.format
                                   (x=os.environ['NZBPO_NDCATEGORY']))
            if 'NZBPO_RACATEGORY' in os.environ and 'NZBPO_CPSCATEGORY' in os.environ:
                if os.environ['NZBPO_RACATEGORY'] == os.environ['NZBPO_CPSCATEGORY']:
                    logger.warning('{x} category is set for CouchPotato and Radarr. '
                                   'Please check your config in NZBGet'.format
                                   (x=os.environ['NZBPO_RACATEGORY']))
            if 'NZBPO_RACATEGORY' in os.environ and 'NZBPO_W3CATEGORY' in os.environ:
                if os.environ['NZBPO_RACATEGORY'] == os.environ['NZBPO_W3CATEGORY']:
                    logger.warning('{x} category is set for Watcher3 and Radarr. '
                                   'Please check your config in NZBGet'.format
                                   (x=os.environ['NZBPO_RACATEGORY']))
            if 'NZBPO_W3CATEGORY' in os.environ and 'NZBPO_CPSCATEGORY' in os.environ:
                if os.environ['NZBPO_W3CATEGORY'] == os.environ['NZBPO_CPSCATEGORY']:
                    logger.warning('{x} category is set for CouchPotato and Watcher3. '
                                   'Please check your config in NZBGet'.format
                                   (x=os.environ['NZBPO_W3CATEGORY']))
            if 'NZBPO_LICATEGORY' in os.environ and 'NZBPO_HPCATEGORY' in os.environ:
                if os.environ['NZBPO_LICATEGORY'] == os.environ['NZBPO_HPCATEGORY']:
                    logger.warning('{x} category is set for HeadPhones and Lidarr. '
                                   'Please check your config in NZBGet'.format
                                   (x=os.environ['NZBPO_LICATEGORY']))
            section = 'Nzb'
            key = 'NZBOP_DESTDIR'
            if key in os.environ:
                option = 'default_downloadDirectory'
                value = os.environ[key]
                cfg_new[section][option] = value

            section = 'General'
            env_keys = ['AUTO_UPDATE', 'CHECK_MEDIA', 'REQUIRE_LAN', 'SAFE_MODE', 'NO_EXTRACT_FAILED']
            cfg_keys = ['auto_update', 'check_media', 'require_lan', 'safe_mode', 'no_extract_failed']
            for index in range(len(env_keys)):
                key = 'NZBPO_{index}'.format(index=env_keys[index])
                if key in os.environ:
                    option = cfg_keys[index]
                    value = os.environ[key]
                    cfg_new[section][option] = value

            section = 'Network'
            env_keys = ['MOUNTPOINTS']
            cfg_keys = ['mount_points']
            for index in range(len(env_keys)):
                key = 'NZBPO_{index}'.format(index=env_keys[index])
                if key in os.environ:
                    option = cfg_keys[index]
                    value = os.environ[key]
                    cfg_new[section][option] = value

            section = 'CouchPotato'
            env_cat_key = 'NZBPO_CPSCATEGORY'
            env_keys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'METHOD', 'DELETE_FAILED', 'REMOTE_PATH',
                        'WAIT_FOR', 'WATCH_DIR', 'OMDBAPIKEY']
            cfg_keys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'method', 'delete_failed', 'remote_path',
                        'wait_for', 'watch_dir', 'omdbapikey']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_CPS{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1
                if os.environ[env_cat_key] in cfg_new['Radarr'].sections:
                    cfg_new['Radarr'][env_cat_key]['enabled'] = 0
                if os.environ[env_cat_key] in cfg_new['Watcher3'].sections:
                    cfg_new['Watcher3'][env_cat_key]['enabled'] = 0

            section = 'Watcher3'
            env_cat_key = 'NZBPO_W3CATEGORY'
            env_keys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'METHOD', 'DELETE_FAILED', 'REMOTE_PATH',
                        'WAIT_FOR', 'WATCH_DIR', 'OMDBAPIKEY']
            cfg_keys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'method', 'delete_failed', 'remote_path',
                        'wait_for', 'watch_dir', 'omdbapikey']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_W3{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1
                if os.environ[env_cat_key] in cfg_new['Radarr'].sections:
                    cfg_new['Radarr'][env_cat_key]['enabled'] = 0
                if os.environ[env_cat_key] in cfg_new['CouchPotato'].sections:
                    cfg_new['CouchPotato'][env_cat_key]['enabled'] = 0

            section = 'SickBeard'
            env_cat_key = 'NZBPO_SBCATEGORY'
            env_keys = ['ENABLED', 'HOST', 'PORT', 'APIKEY', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED', 'TORRENT_NOLINK',
                        'NZBEXTRACTIONBY', 'REMOTE_PATH', 'PROCESS_METHOD']
            cfg_keys = ['enabled', 'host', 'port', 'apikey', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed', 'Torrent_NoLink',
                        'nzbExtractionBy', 'remote_path', 'process_method']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_SB{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1
                if os.environ[env_cat_key] in cfg_new['SiCKRAGE'].sections:
                    cfg_new['SiCKRAGE'][env_cat_key]['enabled'] = 0
                if os.environ[env_cat_key] in cfg_new['NzbDrone'].sections:
                    cfg_new['NzbDrone'][env_cat_key]['enabled'] = 0

            section = 'SiCKRAGE'
            env_cat_key = 'NZBPO_SRCATEGORY'
            env_keys = ['ENABLED', 'HOST', 'PORT', 'APIKEY', 'API_VERSION', 'SSO_USERNAME', 'SSO_PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK',
                        'DELETE_FAILED', 'TORRENT_NOLINK', 'NZBEXTRACTIONBY', 'REMOTE_PATH', 'PROCESS_METHOD']
            cfg_keys = ['enabled', 'host', 'port', 'apikey', 'api_version', 'sso_username', 'sso_password', 'ssl', 'web_root', 'watch_dir', 'fork',
                        'delete_failed', 'Torrent_NoLink', 'nzbExtractionBy', 'remote_path', 'process_method']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_SR{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1
                if os.environ[env_cat_key] in cfg_new['SickBeard'].sections:
                    cfg_new['SickBeard'][env_cat_key]['enabled'] = 0
                if os.environ[env_cat_key] in cfg_new['NzbDrone'].sections:
                    cfg_new['NzbDrone'][env_cat_key]['enabled'] = 0

            section = 'HeadPhones'
            env_cat_key = 'NZBPO_HPCATEGORY'
            env_keys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'WAIT_FOR', 'WATCH_DIR', 'REMOTE_PATH', 'DELETE_FAILED']
            cfg_keys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'wait_for', 'watch_dir', 'remote_path', 'delete_failed']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_HP{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1
                if os.environ[env_cat_key] in cfg_new['Lidarr'].sections:
                    cfg_new['Lidarr'][env_cat_key]['enabled'] = 0

            section = 'Mylar'
            env_cat_key = 'NZBPO_MYCATEGORY'
            env_keys = ['ENABLED', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'APIKEY', 'SSL', 'WEB_ROOT', 'WATCH_DIR',
                        'REMOTE_PATH']
            cfg_keys = ['enabled', 'host', 'port', 'username', 'password', 'apikey', 'ssl', 'web_root', 'watch_dir',
                        'remote_path']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_MY{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1

            section = 'Gamez'
            env_cat_key = 'NZBPO_GZCATEGORY'
            env_keys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'LIBRARY', 'REMOTE_PATH']
            cfg_keys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'watch_dir', 'library', 'remote_path']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_GZ{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1

            section = 'LazyLibrarian'
            env_cat_key = 'NZBPO_LLCATEGORY'
            env_keys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'REMOTE_PATH']
            cfg_keys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'watch_dir', 'remote_path']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_LL{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1

            section = 'NzbDrone'
            env_cat_key = 'NZBPO_NDCATEGORY'
            env_keys = ['ENABLED', 'HOST', 'APIKEY', 'PORT', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED',
                        'TORRENT_NOLINK', 'NZBEXTRACTIONBY', 'WAIT_FOR', 'DELETE_FAILED', 'REMOTE_PATH', 'IMPORTMODE']
            # new cfgKey added for importMode
            cfg_keys = ['enabled', 'host', 'apikey', 'port', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed',
                        'Torrent_NoLink', 'nzbExtractionBy', 'wait_for', 'delete_failed', 'remote_path', 'importMode']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_ND{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1
                if os.environ[env_cat_key] in cfg_new['SickBeard'].sections:
                    cfg_new['SickBeard'][env_cat_key]['enabled'] = 0
                if os.environ[env_cat_key] in cfg_new['SiCKRAGE'].sections:
                    cfg_new['SiCKRAGE'][env_cat_key]['enabled'] = 0

            section = 'Radarr'
            env_cat_key = 'NZBPO_RACATEGORY'
            env_keys = ['ENABLED', 'HOST', 'APIKEY', 'PORT', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED',
                        'TORRENT_NOLINK', 'NZBEXTRACTIONBY', 'WAIT_FOR', 'DELETE_FAILED', 'REMOTE_PATH', 'OMDBAPIKEY', 'IMPORTMODE']
            # new cfgKey added for importMode
            cfg_keys = ['enabled', 'host', 'apikey', 'port', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed',
                        'Torrent_NoLink', 'nzbExtractionBy', 'wait_for', 'delete_failed', 'remote_path', 'omdbapikey', 'importMode']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_RA{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1
                if os.environ[env_cat_key] in cfg_new['CouchPotato'].sections:
                    cfg_new['CouchPotato'][env_cat_key]['enabled'] = 0
                if os.environ[env_cat_key] in cfg_new['Wacther3'].sections:
                    cfg_new['Watcher3'][env_cat_key]['enabled'] = 0

            section = 'Lidarr'
            env_cat_key = 'NZBPO_LICATEGORY'
            env_keys = ['ENABLED', 'HOST', 'APIKEY', 'PORT', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED',
                        'TORRENT_NOLINK', 'NZBEXTRACTIONBY', 'WAIT_FOR', 'DELETE_FAILED', 'REMOTE_PATH']
            cfg_keys = ['enabled', 'host', 'apikey', 'port', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed',
                        'Torrent_NoLink', 'nzbExtractionBy', 'wait_for', 'delete_failed', 'remote_path']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_LI{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1
                if os.environ[env_cat_key] in cfg_new['HeadPhones'].sections:
                    cfg_new['HeadPhones'][env_cat_key]['enabled'] = 0

            section = 'Extensions'
            env_keys = ['COMPRESSEDEXTENSIONS', 'MEDIAEXTENSIONS', 'METAEXTENSIONS']
            cfg_keys = ['compressedExtensions', 'mediaExtensions', 'metaExtensions']
            for index in range(len(env_keys)):
                key = 'NZBPO_{index}'.format(index=env_keys[index])
                if key in os.environ:
                    option = cfg_keys[index]
                    value = os.environ[key]
                    cfg_new[section][option] = value

            section = 'Posix'
            env_keys = ['NICENESS', 'IONICE_CLASS', 'IONICE_CLASSDATA']
            cfg_keys = ['niceness', 'ionice_class', 'ionice_classdata']
            for index in range(len(env_keys)):
                key = 'NZBPO_{index}'.format(index=env_keys[index])
                if key in os.environ:
                    option = cfg_keys[index]
                    value = os.environ[key]
                    cfg_new[section][option] = value

            section = 'Transcoder'
            env_keys = ['TRANSCODE', 'DUPLICATE', 'IGNOREEXTENSIONS', 'OUTPUTFASTSTART', 'OUTPUTVIDEOPATH',
                        'PROCESSOUTPUT', 'AUDIOLANGUAGE', 'ALLAUDIOLANGUAGES', 'SUBLANGUAGES',
                        'ALLSUBLANGUAGES', 'EMBEDSUBS', 'BURNINSUBTITLE', 'EXTRACTSUBS', 'EXTERNALSUBDIR',
                        'OUTPUTDEFAULT', 'OUTPUTVIDEOEXTENSION', 'OUTPUTVIDEOCODEC', 'VIDEOCODECALLOW',
                        'OUTPUTVIDEOPRESET', 'OUTPUTVIDEOFRAMERATE', 'OUTPUTVIDEOBITRATE', 'OUTPUTAUDIOCODEC',
                        'AUDIOCODECALLOW', 'OUTPUTAUDIOBITRATE', 'OUTPUTQUALITYPERCENT', 'GETSUBS',
                        'OUTPUTAUDIOTRACK2CODEC', 'AUDIOCODEC2ALLOW', 'OUTPUTAUDIOTRACK2BITRATE',
                        'OUTPUTAUDIOOTHERCODEC', 'AUDIOOTHERCODECALLOW', 'OUTPUTAUDIOOTHERBITRATE',
                        'OUTPUTSUBTITLECODEC', 'OUTPUTAUDIOCHANNELS', 'OUTPUTAUDIOTRACK2CHANNELS',
                        'OUTPUTAUDIOOTHERCHANNELS', 'OUTPUTVIDEORESOLUTION']
            cfg_keys = ['transcode', 'duplicate', 'ignoreExtensions', 'outputFastStart', 'outputVideoPath',
                        'processOutput', 'audioLanguage', 'allAudioLanguages', 'subLanguages',
                        'allSubLanguages', 'embedSubs', 'burnInSubtitle', 'extractSubs', 'externalSubDir',
                        'outputDefault', 'outputVideoExtension', 'outputVideoCodec', 'VideoCodecAllow',
                        'outputVideoPreset', 'outputVideoFramerate', 'outputVideoBitrate', 'outputAudioCodec',
                        'AudioCodecAllow', 'outputAudioBitrate', 'outputQualityPercent', 'getSubs',
                        'outputAudioTrack2Codec', 'AudioCodec2Allow', 'outputAudioTrack2Bitrate',
                        'outputAudioOtherCodec', 'AudioOtherCodecAllow', 'outputAudioOtherBitrate',
                        'outputSubtitleCodec', 'outputAudioChannels', 'outputAudioTrack2Channels',
                        'outputAudioOtherChannels', 'outputVideoResolution']
            for index in range(len(env_keys)):
                key = 'NZBPO_{index}'.format(index=env_keys[index])
                if key in os.environ:
                    option = cfg_keys[index]
                    value = os.environ[key]
                    cfg_new[section][option] = value

            section = 'WakeOnLan'
            env_keys = ['WAKE', 'HOST', 'PORT', 'MAC']
            cfg_keys = ['wake', 'host', 'port', 'mac']
            for index in range(len(env_keys)):
                key = 'NZBPO_WOL{index}'.format(index=env_keys[index])
                if key in os.environ:
                    option = cfg_keys[index]
                    value = os.environ[key]
                    cfg_new[section][option] = value

            section = 'UserScript'
            env_cat_key = 'NZBPO_USCATEGORY'
            env_keys = ['USER_SCRIPT_MEDIAEXTENSIONS', 'USER_SCRIPT_PATH', 'USER_SCRIPT_PARAM', 'USER_SCRIPT_RUNONCE',
                        'USER_SCRIPT_SUCCESSCODES', 'USER_SCRIPT_CLEAN', 'USDELAY', 'USREMOTE_PATH']
            cfg_keys = ['user_script_mediaExtensions', 'user_script_path', 'user_script_param', 'user_script_runOnce',
                        'user_script_successCodes', 'user_script_clean', 'delay', 'remote_path']
            if env_cat_key in os.environ:
                for index in range(len(env_keys)):
                    key = 'NZBPO_{index}'.format(index=env_keys[index])
                    if key in os.environ:
                        option = cfg_keys[index]
                        value = os.environ[key]
                        if os.environ[env_cat_key] not in cfg_new[section].sections:
                            cfg_new[section][os.environ[env_cat_key]] = {}
                        cfg_new[section][os.environ[env_cat_key]][option] = value
                cfg_new[section][os.environ[env_cat_key]]['enabled'] = 1

        except Exception as error:
            logger.debug('Error {msg} when applying NZBGet config'.format(msg=error))

        try:
            # write our new config to autoProcessMedia.cfg
            cfg_new.filename = core.CONFIG_FILE
            cfg_new.write()
        except Exception as error:
            logger.debug('Error {msg} when writing changes to .cfg'.format(msg=error))

        return cfg_new


configobj.Section = Section
configobj.ConfigObj = ConfigObj
config = ConfigObj
