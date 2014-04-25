import os
import shutil
import nzbtomedia
from configobj import *

from itertools import chain

class Section(configobj.Section):
    def isenabled(section):
        # checks if subsection enabled, returns true/false if subsection specified otherwise returns true/false in {}
        if not section.sections:
            if not int(section['enabled']) == 1:
                return
        else:
            for section_name, subsections in section.items():
                if subsections.sections:
                    for subsection in subsections:
                        if not int(subsections[subsection]['enabled']) == 1:
                            subsections.pop(subsection)
                else:
                    if not int(subsections['enabled']) == 1:
                        section.pop(section_name)

                if len(section[section_name]) == 0:
                    section.pop(section_name)
        return section

    def findsection(section, key):
        for subsection in section:
            if key not in section[subsection]:
                section.pop(subsection)
        return section

    def __getitem__(self, key):
        if key in self.keys():
            return dict.__getitem__(self, key)

        for section, subsections in self.items():
            if section in key:
                continue
            if isinstance(subsections, Section) and subsections.sections:
                for subsection, options in subsections.items():
                    if subsection in key:
                        continue
                    if key in options:
                        return options[key]

                    subsections.pop(subsection)
            else:
                if section not in key:
                    self.pop(section)

            if len(subsections) == 0:
                self.pop(section)

        return self

class ConfigObj(configobj.ConfigObj, Section):
    def __init__(self, *args, **kw):
        if len(args) == 0:
            args = (nzbtomedia.CONFIG_FILE,)
        super(configobj.ConfigObj, self).__init__(*args, **kw)
        self.interpolation = False

    @staticmethod
    def migrate():
        global CFG_NEW, CFG_OLD
        CFG_NEW = None
        CFG_OLD = None

        try:
            # check for autoProcessMedia.cfg and create if it does not exist
            if not os.path.isfile(nzbtomedia.CONFIG_FILE):
                shutil.copyfile(nzbtomedia.CONFIG_SPEC_FILE, nzbtomedia.CONFIG_FILE)
            CFG_OLD = config(nzbtomedia.CONFIG_FILE)
        except:
            pass

        try:
            # check for autoProcessMedia.cfg.spec and create if it does not exist
            if not os.path.isfile(nzbtomedia.CONFIG_SPEC_FILE):
                shutil.copyfile(nzbtomedia.CONFIG_FILE, nzbtomedia.CONFIG_SPEC_FILE)
            CFG_NEW = config(nzbtomedia.CONFIG_SPEC_FILE)
        except:
            pass

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
                if option in ["category", "cpsCategory", "sbCategory", "hpCategory", "mlCategory", "gzCategory"]:
                    if not isinstance(value, list):
                        value = [value]

                    # add subsection
                    subsections.update({section: value})
                    CFG_OLD[section].pop(option)
                    continue

        def cleanup_values(values, section):
            for option, value in values.iteritems():
                if section in ['CouchPotato']:
                    if option == ['outputDirectory']:
                        CFG_NEW['Torrent'][option] = os.path.split(os.path.normpath(value))[0]
                        values.pop(option)
                if section in ['CouchPotato', 'HeadPhones', 'Gamez']:
                    if option in ['username', 'password']:
                        values.pop(option)
                if section in ["SickBeard", "NzbDrone"]:
                    if option == "wait_for":  # remove old format
                        values.pop(option)
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
                        if isinstance(value, int):
                            num_value = int(value)
                            if num_value == 1:
                                value = 'hard'
                            else:
                                value = 'no'
                    if option == "forceClean":
                        CFG_NEW['General']['force_clean'] = value
                        values.pop(option)

                # remove any options that we no longer need so they don't migrate into our new config
                def find_key(node, kv):
                    if isinstance(node, list):
                        for i in node:
                            for x in find_key(i, kv):
                                yield x
                    elif isinstance(node, dict):
                        if kv in node:
                            yield node[kv]
                        for j in node.values():
                            for x in find_key(j, kv):
                                yield x

                if not list(find_key(CFG_NEW, option)):
                    values.pop(option)

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
                section = ''.join([k for k,v in subsections.iteritems() if subsection in v])
                process_section(section, subsection)
            elif section in subsections.keys():
                subsection = subsections[section]
                process_section(section, subsection)
            elif section in CFG_OLD.keys():
                process_section(section, subsection)

        # create a backup of our old config
        CFG_OLD.filename = nzbtomedia.CONFIG_FILE + ".old"
        CFG_OLD.write()

        # write our new config to autoProcessMedia.cfg
        CFG_NEW.filename = nzbtomedia.CONFIG_FILE
        CFG_NEW.write()

        return True

    @staticmethod
    def addnzbget():
        # load configs into memory
        CFG_NEW = config()

        try:
            section = "General"
            envKeys = ['AUTO_UPDATE']
            cfgKeys = ['auto_update']
            for index in range(len(envKeys)):
                key = 'NZBPO_' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    CFG_NEW[section][option] = value

            section = "CouchPotato"
            envCatKey = 'NZBPO_CPSCATEGORY'
            envKeys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'METHOD', 'DELETE_FAILED', 'REMOTECPS', 'WAIT_FOR', 'WATCH_DIR']
            cfgKeys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'method', 'delete_failed', 'remoteCPS', 'wait_for', 'watch_dir']
            if os.environ.has_key(envCatKey):
                for index in range(len(envKeys)):
                    key = 'NZBPO_CPS' + envKeys[index]
                    if os.environ.has_key(key):
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1

            section = "SickBeard"
            envCatKey = 'NZBPO_SBCATEGORY'
            envKeys = ['ENABLED', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED', 'TORRENT_NOLINK', 'NZBEXTRACTIONBY']
            cfgKeys = ['enabled', 'host', 'port', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed', 'Torrent_NoLink', 'nzbExtractionBy']
            if os.environ.has_key(envCatKey):
                for index in range(len(envKeys)):
                    key = 'NZBPO_SB' + envKeys[index]
                    if os.environ.has_key(key):
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1

            section = "HeadPhones"
            envCatKey = 'NZBPO_HPCATEGORY'
            envKeys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'WAIT_FOR', 'WATCH_DIR']
            cfgKeys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'wait_for', 'watch_dir']
            if os.environ.has_key(envCatKey):
                for index in range(len(envKeys)):
                    key = 'NZBPO_HP' + envKeys[index]
                    if os.environ.has_key(key):
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1

            section = "Mylar"
            envCatKey = 'NZBPO_MYCATEGORY'
            envKeys = ['ENABLED', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR']
            cfgKeys = ['enabled', 'host', 'port', 'username', 'password', 'ssl', 'web_root', 'watch_dir']
            if os.environ.has_key(envCatKey):
                for index in range(len(envKeys)):
                    key = 'NZBPO_MY' + envKeys[index]
                    if os.environ.has_key(key):
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1

            section = "Gamez"
            envCatKey = 'NZBPO_GZCATEGORY'
            envKeys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'WATCH_DIR']
            cfgKeys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'watch_dir']
            if os.environ.has_key(envCatKey):
                for index in range(len(envKeys)):
                    key = 'NZBPO_GZ' + envKeys[index]
                    if os.environ.has_key(key):
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1

            section = "NzbDrone"
            envCatKey = 'NZBPO_NDCATEGORY'
            envKeys = ['ENABLED', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED', 'TORRENT_NOLINK', 'NZBEXTRACTIONBY']
            cfgKeys = ['enabled', 'host', 'port', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed', 'Torrent_NoLink', 'nzbExtractionBy']
            if os.environ.has_key(envCatKey):
                for index in range(len(envKeys)):
                    key = 'NZBPO_ND' + envKeys[index]
                    if os.environ.has_key(key):
                        option = cfgKeys[index]
                        value = os.environ[key]
                        if os.environ[envCatKey] not in CFG_NEW[section].sections:
                            CFG_NEW[section][os.environ[envCatKey]] = {}
                        CFG_NEW[section][os.environ[envCatKey]][option] = value
                CFG_NEW[section][os.environ[envCatKey]]['enabled'] = 1

            section = "Extensions"
            envKeys = ['COMPRESSEDEXTENSIONS', 'MEDIAEXTENSIONS', 'METAEXTENSIONS']
            cfgKeys = ['compressedExtensions', 'mediaExtensions', 'metaExtensions']
            for index in range(len(envKeys)):
                key = 'NZBPO_' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    CFG_NEW[section][option] = value

            section = "Transcoder"
            envKeys = ['TRANSCODE', 'DUPLICATE', 'IGNOREEXTENSIONS', 'OUTPUTVIDEOEXTENSION', 'OUTPUTVIDEOCODEC', 'OUTPUTVIDEOPRESET', 'OUTPUTVIDEOFRAMERATE', 'OUTPUTVIDEOBITRATE', 'OUTPUTAUDIOCODEC', 'OUTPUTAUDIOBITRATE', 'OUTPUTSUBTITLECODEC']
            cfgKeys = ['transcode', 'duplicate', 'ignoreExtensions', 'outputVideoExtension', 'outputVideoCodec', 'outputVideoPreset', 'outputVideoFramerate', 'outputVideoBitrate', 'outputAudioCodec', 'outputAudioBitrate', 'outputSubtitleCodec']
            for index in range(len(envKeys)):
                key = 'NZBPO_' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    CFG_NEW[section][option] = value

            section = "WakeOnLan"
            envKeys = ['WAKE', 'HOST', 'PORT', 'MAC']
            cfgKeys = ['wake', 'host', 'port', 'mac']
            for index in range(len(envKeys)):
                key = 'NZBPO_WOL' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    CFG_NEW[section][option] = value

        except:
            return False

        # write our new config to autoProcessMedia.cfg
        CFG_NEW.filename = nzbtomedia.CONFIG_FILE
        CFG_NEW.write()

        return True

configobj.Section = Section
configobj.ConfigObj = ConfigObj
config = ConfigObj
