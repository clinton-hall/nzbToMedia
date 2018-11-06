# coding=utf-8

from six import iteritems
import os
import shutil
import copy
import core
from configobj import *
from core import logger

from itertools import chain


class Section(configobj.Section, object):
    def isenabled(section):
        # checks if subsection enabled, returns true/false if subsection specified otherwise returns true/false in {}
        if not section.sections:
            try:
                value = list(ConfigObj.find_key(section, 'enabled'))[0]
            except:
                value = 0
            if int(value) == 1:
                return section
        else:
            to_return = copy.deepcopy(section)
            for section_name, subsections in to_return.items():
                for subsection in subsections:
                    try:
                        value = list(ConfigObj.find_key(subsections, 'enabled'))[0]
                    except:
                        value = 0

                    if int(value) != 1:
                        del to_return[section_name][subsection]

            # cleanout empty sections and subsections
            for key in [k for (k, v) in to_return.items() if not v]:
                del to_return[key]

            return to_return

    def findsection(section, key):
        to_return = copy.deepcopy(section)
        for subsection in to_return:
            try:
                value = list(ConfigObj.find_key(to_return[subsection], key))[0]
            except:
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
            logger.debug("Error {msg} when copying to .cfg".format(msg=error))

        try:
            # check for autoProcessMedia.cfg.spec and create if it does not exist
            if not os.path.isfile(core.CONFIG_SPEC_FILE):
                shutil.copyfile(core.CONFIG_FILE, core.CONFIG_SPEC_FILE)
            CFG_NEW = config(core.CONFIG_SPEC_FILE)
        except Exception as error:
            logger.debug("Error {msg} when copying to .spec".format(msg=error))

        # check for autoProcessMedia.cfg and autoProcessMedia.cfg.spec and if they don't exist return and fail
        if CFG_NEW is None or CFG_OLD is None:
            return False

        subsections = {}
        # gather all new-style and old-style sub-sections
        for newsection, newitems in CFG_NEW.items():
            if CFG_NEW[newsection].sections:
                subsections.update({newsection: CFG_NEW[newsection].sections})
        for section, items in CFG_OLD.items():
            if CFG_OLD[section].sections:
                subsections.update({section: CFG_OLD[section].sections})
            for option, value in CFG_OLD[section].items():
                if option in ["category", "cpsCategory", "sbCategory", "hpCategory", "mlCategory", "gzCategory", "raCategory", "ndCategory"]:
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
                if section in ["SickBeard", "Mylar"]:
                    if option == "wait_for":  # remove old format
                        values.pop(option)
                if section in ["SickBeard", "NzbDrone"]:
                    if option == "failed_fork":  # change this old format
                        values['failed'] = 'auto'
                        values.pop(option)
                    if option == "outputDirectory":  # move this to new location format
                        CFG_NEW['Torrent'][option] = os.path.split(os.path.normpath(value))[0]
                        values.pop(option)
                if section in ["Torrent"]:
                    if option in ["compressedExtensions", "mediaExtensions", "metaExtensions", "minSampleSize"]:
                        CFG_NEW['Extensions'][option] = value
                        values.pop(option)
                    if option == "useLink":  # Sym links supported now as well.
                        if value in ['1', 1]:
                            value = 'hard'
                        elif value in ['0', 0]:
                            value = 'no'
                        values[option] = value
                    if option == "forceClean":
                        CFG_NEW['General']['force_clean'] = value
                        values.pop(option)
                if section in ["Transcoder"]:
                    if option in ["niceness"]:
                        CFG_NEW['Posix'][option] = value
                        values.pop(option)
                if option == "remote_path":
                    if value and value not in ['0', '1', 0, 1]:
                        value = 1
                    elif not value:
                        value = 0
                    values[option] = value
                # remove any options that we no longer need so they don't migrate into our new config
                if not list(ConfigObj.find_key(CFG_NEW, option)):
                    try:
                        values.pop(option)
                    except:
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

        # create a backup of our old config
        CFG_OLD.filename ="{config}.old".format(config=core.CONFIG_FILE)
        CFG_OLD.write()

        # write our new config to autoProcessMedia.cfg
        CFG_NEW.filename = core.CONFIG_FILE
        CFG_NEW.write()

        return True

    @staticmethod
    def addnzbget():
        # load configs into memory
        CFG_NEW = config()

        try:
            if 'NZBPO_NDCATEGORY' in os.environ and 'NZBPO_SBCATEGORY' in os.environ:
                if os.environ['NZBPO_NDCATEGORY'] == os.environ['NZBPO_SBCATEGORY']:
                    logger.warning("{x} category is set for SickBeard and Sonarr. "
                                   "Please check your config in NZBGet".format
                                   (x=os.environ['NZBPO_NDCATEGORY']))
            if 'NZBPO_RACATEGORY' in os.environ and 'NZBPO_CPSCATEGORY' in os.environ:
                if os.environ['NZBPO_RACATEGORY'] == os.environ['NZBPO_CPSCATEGORY']:
                    logger.warning("{x} category is set for CouchPotato and Radarr. "
                                   "Please check your config in NZBGet".format
                                   (x=os.environ['NZBPO_RACATEGORY']))
            if 'NZBPO_LICATEGORY' in os.environ and 'NZBPO_HPCATEGORY' in os.environ:
                if os.environ['NZBPO_LICATEGORY'] == os.environ['NZBPO_HPCATEGORY']:
                    logger.warning("{x} category is set for HeadPhones and Lidarr. "
                                   "Please check your config in NZBGet".format
                                   (x=os.environ['NZBPO_LICATEGORY']))
            section = "Nzb"
            key = 'NZBOP_DESTDIR'
            if key in os.environ:
                option = 'default_downloadDirectory'
                value = os.environ[key]
                CFG_NEW[section][option] = value

            section = "General"
            envKeys = ['AUTO_UPDATE', 'CHECK_MEDIA', 'SAFE_MODE', 'NO_EXTRACT_FAILED']
            cfgKeys = ['auto_update', 'check_media', 'safe_mode', 'no_extract_failed']
            for index in range(len(envKeys)):
                key = 'NZBPO_{index}'.format(index=envKeys[index])
                if key in os.environ:
                    option = cfgKeys[index]
                    value = os.environ[key]
                    CFG_NEW[section][option] = value

            section = "Network"
            envKeys = ['MOUNTPOINTS']
            cfgKeys = ['mount_points']
            for index in range(len(envKeys)):
                key = 'NZBPO_{index}'.format(index=envKeys[index])
                if key in os.environ:
                    option = cfgKeys[index]
                    value = os.environ[key]
                    CFG_NEW[section][option] = value

            section = "CouchPotato"
            envCatKey = 'NZBPO_CPSCATEGORY'
            envKeys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'METHOD', 'DELETE_FAILED', 'REMOTE_PATH',
                       'WAIT_FOR', 'WATCH_DIR', 'OMDBAPIKEY']
            cfgKeys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'method', 'delete_failed', 'remote_path',
                       'wait_for', 'watch_dir', 'omdbapikey']
            if envCatKey in os.environ:
                for index in range(len(envKeys)):
                    key = 'NZBPO_CPS{index}'.format(index=envKeys[index])
                    if key in os.environ:
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1
                if os.environ[envCatKey] in CFG_NEW['Radarr'].sections:
                    CFG_NEW['Radarr'][envCatKey]['enabled'] = 0

            section = "SickBeard"
            envCatKey = 'NZBPO_SBCATEGORY'
            envKeys = ['ENABLED', 'HOST', 'PORT', 'APIKEY', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK',
                       'DELETE_FAILED', 'TORRENT_NOLINK', 'NZBEXTRACTIONBY', 'REMOTE_PATH', 'PROCESS_METHOD']
            cfgKeys = ['enabled', 'host', 'port', 'apikey', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork',
                       'delete_failed', 'Torrent_NoLink', 'nzbExtractionBy', 'remote_path', 'process_method']
            if envCatKey in os.environ:
                for index in range(len(envKeys)):
                    key = 'NZBPO_SB{index}'.format(index=envKeys[index])
                    if key in os.environ:
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1
                if os.environ[envCatKey] in CFG_NEW['NzbDrone'].sections:
                    CFG_NEW['NzbDrone'][envCatKey]['enabled'] = 0

            section = "HeadPhones"
            envCatKey = 'NZBPO_HPCATEGORY'
            envKeys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'WAIT_FOR', 'WATCH_DIR', 'REMOTE_PATH', 'DELETE_FAILED']
            cfgKeys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'wait_for', 'watch_dir', 'remote_path', 'delete_failed']
            if envCatKey in os.environ:
                for index in range(len(envKeys)):
                    key = 'NZBPO_HP{index}'.format(index=envKeys[index])
                    if key in os.environ:
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1
                if os.environ[envCatKey] in CFG_NEW['Lidarr'].sections:
                    CFG_NEW['Lidarr'][envCatKey]['enabled'] = 0

            section = "Mylar"
            envCatKey = 'NZBPO_MYCATEGORY'
            envKeys = ['ENABLED', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'APIKEY', 'SSL', 'WEB_ROOT', 'WATCH_DIR',
                       'REMOTE_PATH']
            cfgKeys = ['enabled', 'host', 'port', 'username', 'password', 'apikey', 'ssl', 'web_root', 'watch_dir',
                       'remote_path']
            if envCatKey in os.environ:
                for index in range(len(envKeys)):
                    key = 'NZBPO_MY{index}'.format(index=envKeys[index])
                    if key in os.environ:
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1

            section = "Gamez"
            envCatKey = 'NZBPO_GZCATEGORY'
            envKeys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'LIBRARY', 'REMOTE_PATH']
            cfgKeys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'watch_dir', 'library', 'remote_path']
            if envCatKey in os.environ:
                for index in range(len(envKeys)):
                    key = 'NZBPO_GZ{index}'.format(index=envKeys[index])
                    if key in os.environ:
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1

            section = "NzbDrone"
            envCatKey = 'NZBPO_NDCATEGORY'
            envKeys = ['ENABLED', 'HOST', 'APIKEY', 'PORT', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED',
                       'TORRENT_NOLINK', 'NZBEXTRACTIONBY', 'WAIT_FOR', 'DELETE_FAILED', 'REMOTE_PATH', 'IMPORTMODE']
            #new cfgKey added for importMode
            cfgKeys = ['enabled', 'host', 'apikey', 'port', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed',
                       'Torrent_NoLink', 'nzbExtractionBy', 'wait_for', 'delete_failed', 'remote_path','importMode']
            if envCatKey in os.environ:
                for index in range(len(envKeys)):
                    key = 'NZBPO_ND{index}'.format(index=envKeys[index])
                    if key in os.environ:
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1
                if os.environ[envCatKey] in CFG_NEW['SickBeard'].sections:
                    CFG_NEW['SickBeard'][envCatKey]['enabled'] = 0

            section = "Radarr"
            envCatKey = 'NZBPO_RACATEGORY'
            envKeys = ['ENABLED', 'HOST', 'APIKEY', 'PORT', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED',
                       'TORRENT_NOLINK', 'NZBEXTRACTIONBY', 'WAIT_FOR', 'DELETE_FAILED', 'REMOTE_PATH', 'OMDBAPIKEY', 'IMPORTMODE']
            #new cfgKey added for importMode
            cfgKeys = ['enabled', 'host', 'apikey', 'port', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed',
                       'Torrent_NoLink', 'nzbExtractionBy', 'wait_for', 'delete_failed', 'remote_path', 'omdbapikey','importMode']
            if envCatKey in os.environ:
                for index in range(len(envKeys)):
                    key = 'NZBPO_RA{index}'.format(index=envKeys[index])
                    if key in os.environ:
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1
                if os.environ[envCatKey] in CFG_NEW['CouchPotato'].sections:
                    CFG_NEW['CouchPotato'][envCatKey]['enabled'] = 0

            section = "Lidarr"
            envCatKey = 'NZBPO_LICATEGORY'
            envKeys = ['ENABLED', 'HOST', 'APIKEY', 'PORT', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED',
                       'TORRENT_NOLINK', 'NZBEXTRACTIONBY', 'WAIT_FOR', 'DELETE_FAILED', 'REMOTE_PATH']
            cfgKeys = ['enabled', 'host', 'apikey', 'port', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed',
                       'Torrent_NoLink', 'nzbExtractionBy', 'wait_for', 'delete_failed', 'remote_path']
            if envCatKey in os.environ:
                for index in range(len(envKeys)):
                    key = 'NZBPO_LI{index}'.format(index=envKeys[index])
                    if key in os.environ:
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1
                if os.environ[envCatKey] in CFG_NEW['HeadPhones'].sections:
                    CFG_NEW['HeadPhones'][envCatKey]['enabled'] = 0

            section = "Extensions"
            envKeys = ['COMPRESSEDEXTENSIONS', 'MEDIAEXTENSIONS', 'METAEXTENSIONS']
            cfgKeys = ['compressedExtensions', 'mediaExtensions', 'metaExtensions']
            for index in range(len(envKeys)):
                key = 'NZBPO_{index}'.format(index=envKeys[index])
                if key in os.environ:
                    option = cfgKeys[index]
                    value = os.environ[key]
                    CFG_NEW[section][option] = value

            section = "Posix"
            envKeys = ['NICENESS', 'IONICE_CLASS', 'IONICE_CLASSDATA']
            cfgKeys = ['niceness', 'ionice_class', 'ionice_classdata']
            for index in range(len(envKeys)):
                key = 'NZBPO_{index}'.format(index=envKeys[index])
                if key in os.environ:
                    option = cfgKeys[index]
                    value = os.environ[key]
                    CFG_NEW[section][option] = value

            section = "Transcoder"
            envKeys = ['TRANSCODE', 'DUPLICATE', 'IGNOREEXTENSIONS', 'OUTPUTFASTSTART', 'OUTPUTVIDEOPATH',
                       'PROCESSOUTPUT', 'AUDIOLANGUAGE', 'ALLAUDIOLANGUAGES', 'SUBLANGUAGES',
                       'ALLSUBLANGUAGES', 'EMBEDSUBS', 'BURNINSUBTITLE', 'EXTRACTSUBS', 'EXTERNALSUBDIR',
                       'OUTPUTDEFAULT', 'OUTPUTVIDEOEXTENSION', 'OUTPUTVIDEOCODEC', 'VIDEOCODECALLOW',
                       'OUTPUTVIDEOPRESET', 'OUTPUTVIDEOFRAMERATE', 'OUTPUTVIDEOBITRATE', 'OUTPUTAUDIOCODEC',
                       'AUDIOCODECALLOW', 'OUTPUTAUDIOBITRATE', 'OUTPUTQUALITYPERCENT', 'GETSUBS',
                       'OUTPUTAUDIOTRACK2CODEC', 'AUDIOCODEC2ALLOW', 'OUTPUTAUDIOTRACK2BITRATE',
                       'OUTPUTAUDIOOTHERCODEC', 'AUDIOOTHERCODECALLOW', 'OUTPUTAUDIOOTHERBITRATE',
                       'OUTPUTSUBTITLECODEC', 'OUTPUTAUDIOCHANNELS', 'OUTPUTAUDIOTRACK2CHANNELS',
                       'OUTPUTAUDIOOTHERCHANNELS','OUTPUTVIDEORESOLUTION']
            cfgKeys = ['transcode', 'duplicate', 'ignoreExtensions', 'outputFastStart', 'outputVideoPath',
                       'processOutput', 'audioLanguage', 'allAudioLanguages', 'subLanguages',
                       'allSubLanguages', 'embedSubs', 'burnInSubtitle', 'extractSubs', 'externalSubDir',
                       'outputDefault', 'outputVideoExtension', 'outputVideoCodec', 'VideoCodecAllow',
                       'outputVideoPreset', 'outputVideoFramerate', 'outputVideoBitrate', 'outputAudioCodec',
                       'AudioCodecAllow', 'outputAudioBitrate', 'outputQualityPercent', 'getSubs',
                       'outputAudioTrack2Codec', 'AudioCodec2Allow', 'outputAudioTrack2Bitrate',
                       'outputAudioOtherCodec', 'AudioOtherCodecAllow', 'outputAudioOtherBitrate',
                       'outputSubtitleCodec', 'outputAudioChannels', 'outputAudioTrack2Channels',
                       'outputAudioOtherChannels', 'outputVideoResolution']
            for index in range(len(envKeys)):
                key = 'NZBPO_{index}'.format(index=envKeys[index])
                if key in os.environ:
                    option = cfgKeys[index]
                    value = os.environ[key]
                    CFG_NEW[section][option] = value

            section = "WakeOnLan"
            envKeys = ['WAKE', 'HOST', 'PORT', 'MAC']
            cfgKeys = ['wake', 'host', 'port', 'mac']
            for index in range(len(envKeys)):
                key = 'NZBPO_WOL{index}'.format(index=envKeys[index])
                if key in os.environ:
                    option = cfgKeys[index]
                    value = os.environ[key]
                    CFG_NEW[section][option] = value

            section = "UserScript"
            envCatKey = 'NZBPO_USCATEGORY'
            envKeys = ['USER_SCRIPT_MEDIAEXTENSIONS', 'USER_SCRIPT_PATH', 'USER_SCRIPT_PARAM', 'USER_SCRIPT_RUNONCE',
                       'USER_SCRIPT_SUCCESSCODES', 'USER_SCRIPT_CLEAN', 'USDELAY', 'USREMOTE_PATH']
            cfgKeys = ['user_script_mediaExtensions', 'user_script_path', 'user_script_param', 'user_script_runOnce',
                       'user_script_successCodes', 'user_script_clean', 'delay', 'remote_path']
            if envCatKey in os.environ:
                for index in range(len(envKeys)):
                    key = 'NZBPO_{index}'.format(index=envKeys[index])
                    if key in os.environ:
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1

        except Exception as error:
            logger.debug("Error {msg} when applying NZBGet config".format(msg=error))

        try:
            # write our new config to autoProcessMedia.cfg
            CFG_NEW.filename = core.CONFIG_FILE
            CFG_NEW.write()
        except Exception as error:
            logger.debug("Error {msg} when writing changes to .cfg".format(msg=error))

        return CFG_NEW


configobj.Section = Section
configobj.ConfigObj = ConfigObj
config = ConfigObj
