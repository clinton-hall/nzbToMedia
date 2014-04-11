import os
import shutil
import lib.configobj
from itertools import chain

class Sections(dict):
    def issubsection(sections, subsection, checkenabled=True):
        # checks sections for subsection, returns true/false in {}
        to_return = False
        for section in sections.values():
            to_return = section.issubsection(subsection, checkenabled)
        return to_return

    def isenabled(sections, subsection):
        # checks if subsections are enabled, returns true/false in {}
        to_return = False
        for section in sections.values():
            to_return = section.isenabled(subsection)
        return to_return

    @property
    def sections(sections):
        # returns [subsections]
        to_return = []
        for section in sections:
            to_return.append(sections[section].sections)
        return list(set(chain.from_iterable(to_return)))

    @property
    def subsections(sections):
        # returns {section name:[subsections]}
        to_return = {}
        for section in sections:
            to_return.update(sections[section].subsections)
        return to_return

class Section(lib.configobj.Section):
    def issubsection(section, subsection, checkenabled=True):
        # checks section for subsection, returns true/false
        to_return = False
        if subsection in section:
            if checkenabled and section.isenabled(subsection):
                to_return = True
            else:
                to_return = True
        return to_return

    def isenabled(section, subsection):
        # checks if subsection enabled, returns true/false if subsection specified otherwise returns true/false in {}
        to_return = False
        if subsection in section and int(section[subsection]['enabled']) == 1:
            to_return = True
        return to_return

    @property
    def subsections(section):
        # returns {section name:[subsections]}
        to_return = {}
        for subsection in section:
            to_return.update({section.name: section.sections})
        return to_return

    def findsection(section, key):
        for subsection in section:
            if key in section[subsection]:
                return subsection

class ConfigObj(lib.configobj.ConfigObj, Section):
    # constants for nzbtomedia
    NZBTOMEDIA_VERSION = 'V9.3'
    NZBTOMEDIA_TIMEOUT = 60

    # Constants pertinant to SabNzb
    SABNZB_NO_OF_ARGUMENTS = 8
    SABNZB_0717_NO_OF_ARGUMENTS = 9

    # Constants pertaining to SickBeard Branches:
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

    # config files
    PROGRAM_DIR = os.path.dirname(os.path.normpath(os.path.abspath(os.path.join(__file__, os.pardir))))
    CONFIG_FILE = os.path.join(PROGRAM_DIR, "autoProcessMedia.cfg")
    SAMPLE_CONFIG_FILE = os.path.join(PROGRAM_DIR, "autoProcessMedia.cfg.sample")
    MOVIE_CONFIG_FILE = os.path.join(PROGRAM_DIR, "autoProcessMovie.cfg")
    TV_CONFIG_FILE = os.path.join(PROGRAM_DIR, "autoProcessTv.cfg")
    LOG_FILE = os.path.join(PROGRAM_DIR, "postprocess.log")
    LOG_CONFIG = os.path.join(PROGRAM_DIR, "logging.cfg")
    SAMPLE_LOG_CONFIG = os.path.join(PROGRAM_DIR, "logging.cfg.sample")

    try:
        repo = check_output(["git", "config", "--get", "remote.origin.url"]).splitlines()[0]
        branch = check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).splitlines()[0]
        hash = check_output(["git", "rev-parse", "--short", "HEAD"]).splitlines()[0]
        NZBTOMEDIA_VERSION = 'repo:' + repo + ' branch:' + branch + ' hash: ' + hash
    except CalledProcessError:
        pass

    def __init__(self, *args, **kw):
        if len(args) == 0:
            args = (self.CONFIG_FILE,)
        super(lib.configobj.ConfigObj, self).__init__(*args, **kw)
        self.interpolation = False

    def __getitem__(self, key):
        result = Sections()
        if isinstance(key, tuple):
            for item in key:
                val = dict.__getitem__(self, item)
                result.update({item: val})
            return result
        else:
            val = dict.__getitem__(self, key)
            #result.update({key: val})
        return val

    def migrate(self):
        global config_new, config_old
        config_new = config_old = None

        try:
            # check for autoProcessMedia.cfg and create if it does not exist
            if not config():
                shutil.copyfile(self.SAMPLE_CONFIG_FILE, self.CONFIG_FILE)
            config_old = config()
        except:
            pass

        try:
            # check for autoProcessMedia.cfg.sample and create if it does not exist
            if not config(self.SAMPLE_CONFIG_FILE):
                shutil.copyfile(self.CONFIG_FILE, self.SAMPLE_CONFIG_FILE)
            config_new = config(self.SAMPLE_CONFIG_FILE)
        except:
            pass

        # check for autoProcessMedia.cfg and autoProcessMedia.cfg.sample and if they don't exist return and fail
        if not config() and not config(self.SAMPLE_CONFIG_FILE) or not config_new or not config_old:
            return False

        subsections = {}
        # gather all new-style and old-style sub-sections
        for newsection, newitems in config_new.items():
            if config_new[newsection].sections:
                subsections.update({newsection: config_new[newsection].sections})
        for section, items in config_old.items():
            if config_old[section].sections:
                subsections.update({section: config_old[section].sections})
            for option, value in config_old[section].items():
                if option in ["category", "cpsCategory", "sbCategory", "hpCategory", "mlCategory", "gzCategory"]:
                    if not isinstance(value, list):
                        value = [value]

                    # add subsection
                    subsections.update({section: value})
                    config_old[section].pop(option)
                    continue

        def cleanup_values(values, section):
            for option, value in values.iteritems():
                if section in ['CouchPotato']:
                    if option == ['outputDirectory']:
                        config_new['Torrent'][option] = os.path.split(os.path.normpath(value))[0]
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
                    if option == "Torrent_ForceLink":
                        values['Torrent_NoLink'] = value
                        values.pop(option)
                    if option == "outputDirectory":  # move this to new location format
                        config_new['Torrent'][option] = os.path.split(os.path.normpath(value))[0]
                        values.pop(option)
                if section in ["Torrent"]:
                    if option in ["compressedExtensions", "mediaExtensions", "metaExtensions", "minSampleSize"]:
                        config_new['Extensions'][option] = value
                        values.pop(option)
                    if option == "useLink":  # Sym links supported now as well.
                        if isinstance(value, int):
                            num_value = int(value)
                            if num_value == 1:
                                value = 'hard'
                            else:
                                value = 'no'
            return values

        def process_section(section, subsections=None):
            if subsections:
                for subsection in subsections:
                    if subsection in config_old.sections:
                        values = config_old[subsection]
                        if subsection not in config_new[section].sections:
                            config_new[section][subsection] = {}
                        for option, value in values.items():
                            config_new[section][subsection][option] = value
                    elif subsection in config_old[section].sections:
                        values = config_old[section][subsection]
                        if subsection not in config_new[section].sections:
                            config_new[section][subsection] = {}
                        for option, value in values.items():
                            config_new[section][subsection][option] = value
            else:
                values = config_old[section]
                if section not in config_new.sections:
                    config_new[section] = {}
                for option, value in values.items():
                    config_new[section][option] = value

        # convert old-style categories to new-style sub-sections
        for section in config_old.keys():
            subsection = None
            if section in list(chain.from_iterable(subsections.values())):
                subsection = section
                section = ''.join([k for k,v in subsections.iteritems() if subsection in v])
                process_section(section, subsection)
                #[[v.remove(c) for c in v if c in subsection] for k, v in subsections.items() if k == section]
            elif section in subsections.keys():
                subsection = subsections[section]
                process_section(section, subsection)
                #[[v.remove(c) for c in v if c in subsection] for k,v in subsections.items() if k == section]
            elif section in config_old.keys():
                process_section(section, subsection)

        # create a backup of our old config
        if os.path.isfile(self.CONFIG_FILE):
            cfgbak_name = self.CONFIG_FILE + ".old"
            if os.path.isfile(cfgbak_name):  # remove older backups
                os.unlink(cfgbak_name)
            os.rename(self.CONFIG_FILE, cfgbak_name)

        # writing our configuration file to 'autoProcessMedia.cfg'
        with open(self.CONFIG_FILE, 'wb') as configFile:
            config_new.write(configFile)

        return True

    def addnzbget(self):
        config_new = config()
        section = "CouchPotato"
        envCatKey = 'NZBPO_CPSCATEGORY'
        envKeys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY', 'METHOD', 'DELETE_FAILED', 'REMOTECPS', 'WAIT_FOR', 'TIMEPERGIB']
        cfgKeys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'delay', 'method', 'delete_failed', 'remoteCPS', 'wait_for', 'TimePerGiB']
        if os.environ.has_key(envCatKey):
            for index in range(len(envKeys)):
                key = 'NZBPO_CPS' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    if os.environ[envCatKey] not in config_new[section].sections:
                        config_new[section][os.environ[envCatKey]] = {}
                    config_new[section][os.environ[envCatKey]][option] = value
            config_new[section][os.environ[envCatKey]]['enabled'] = 1

        section = "SickBeard"
        envCatKey = 'NZBPO_SBCATEGORY'
        envKeys = ['ENABLED', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED', 'DELAY', 'TIMEPERGIB', 'TORRENT_NOLINK', 'NZBEXTRACTIONBY']
        cfgKeys = ['enabled', 'host', 'port', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed', 'delay', 'TimePerGiB', 'Torrent_NoLink', 'nzbExtractionBy']
        if os.environ.has_key(envCatKey):
            for index in range(len(envKeys)):
                key = 'NZBPO_SB' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    if os.environ[envCatKey] not in config_new[section].sections:
                        config_new[section][os.environ[envCatKey]] = {}
                    config_new[section][os.environ[envCatKey]][option] = value
            config_new[section][os.environ[envCatKey]]['enabled'] = 1

        section = "HeadPhones"
        envCatKey = 'NZBPO_HPCATEGORY'
        envKeys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY', 'TIMEPERGIB']
        cfgKeys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root', 'delay', 'TimePerGiB']
        if os.environ.has_key(envCatKey):
            for index in range(len(envKeys)):
                key = 'NZBPO_HP' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    if os.environ[envCatKey] not in config_new[section].sections:
                        config_new[section][os.environ[envCatKey]] = {}
                    config_new[section][os.environ[envCatKey]][option] = value
            config_new[section][os.environ[envCatKey]]['enabled'] = 1

        section = "Mylar"
        envCatKey = 'NZBPO_MYCATEGORY'
        envKeys = ['ENABLED', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT']
        cfgKeys = ['enabled', 'host', 'port', 'username', 'password', 'ssl', 'web_root']
        if os.environ.has_key(envCatKey):
            for index in range(len(envKeys)):
                key = 'NZBPO_MY' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    if os.environ[envCatKey] not in config_new[section].sections:
                        config_new[section][os.environ[envCatKey]] = {}
                    config_new[section][os.environ[envCatKey]][option] = value
            config_new[section][os.environ[envCatKey]]['enabled'] = 1

        section = "Gamez"
        envCatKey = 'NZBPO_GZCATEGORY'
        envKeys = ['ENABLED', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT']
        cfgKeys = ['enabled', 'apikey', 'host', 'port', 'ssl', 'web_root']
        if os.environ.has_key(envCatKey):
            for index in range(len(envKeys)):
                key = 'NZBPO_GZ' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    if os.environ[envCatKey] not in config_new[section].sections:
                        config_new[section][os.environ[envCatKey]] = {}
                    config_new[section][os.environ[envCatKey]][option] = value
            config_new[section][os.environ[envCatKey]]['enabled'] = 1

        section = "NzbDrone"
        envCatKey = 'NZBPO_NDCATEGORY'
        envKeys = ['ENABLED', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED', 'DELAY', 'TIMEPERGIB', 'TORRENT_NOLINK', 'NZBEXTRACTIONBY']
        cfgKeys = ['enabled', 'host', 'port', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed', 'delay', 'TimePerGiB', 'Torrent_NoLink', 'nzbExtractionBy']
        if os.environ.has_key(envCatKey):
            for index in range(len(envKeys)):
                key = 'NZBPO_ND' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    if os.environ[envCatKey] not in config_new[section].sections:
                        config_new[section][os.environ[envCatKey]] = {}
                    config_new[section][os.environ[envCatKey]][option] = value
            config_new[section][os.environ[envCatKey]]['enabled'] = 1

        section = "Extensions"
        envKeys = ['COMPRESSEDEXTENSIONS', 'MEDIAEXTENSIONS', 'METAEXTENSIONS']
        cfgKeys = ['compressedExtensions', 'mediaExtensions', 'metaExtensions']
        for index in range(len(envKeys)):
            key = 'NZBPO_' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                config_new[section][option] = value

        section = "Transcoder"
        envKeys = ['TRANSCODE', 'DUPLICATE', 'IGNOREEXTENSIONS', 'OUTPUTVIDEOEXTENSION', 'OUTPUTVIDEOCODEC', 'OUTPUTVIDEOPRESET', 'OUTPUTVIDEOFRAMERATE', 'OUTPUTVIDEOBITRATE', 'OUTPUTAUDIOCODEC', 'OUTPUTAUDIOBITRATE', 'OUTPUTSUBTITLECODEC']
        cfgKeys = ['transcode', 'duplicate', 'ignoreExtensions', 'outputVideoExtension', 'outputVideoCodec', 'outputVideoPreset', 'outputVideoFramerate', 'outputVideoBitrate', 'outputAudioCodec', 'outputAudioBitrate', 'outputSubtitleCodec']
        for index in range(len(envKeys)):
            key = 'NZBPO_' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                config_new[section][option] = value

        section = "WakeOnLan"
        envKeys = ['WAKE', 'HOST', 'PORT', 'MAC']
        cfgKeys = ['wake', 'host', 'port', 'mac']
        for index in range(len(envKeys)):
            key = 'NZBPO_WOL' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                config_new[section][option] = value

        # create a backup of our old config
        if os.path.isfile(self.CONFIG_FILE):
            cfgbak_name = self.CONFIG_FILE + ".old"
            if os.path.isfile(cfgbak_name):  # remove older backups
                os.unlink(cfgbak_name)
            os.rename(self.CONFIG_FILE, cfgbak_name)

        # writing our configuration file to 'autoProcessMedia.cfg'
        with open(self.CONFIG_FILE, 'wb') as configFile:
            config_new.write(configFile)

lib.configobj.Section = Section
lib.configobj.ConfigObj = ConfigObj
config = ConfigObj
