import os
import shutil
import lib.configobj
from lib.configobj import ConfigObj
from itertools import chain

original_ConfigObj = lib.configobj.ConfigObj
class config(original_ConfigObj):
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

    def __init__(self, *args, **kw):
        if len(args) == 0:
            args = (self.CONFIG_FILE,)
        super(lib.configobj.ConfigObj, self).__init__(*args, **kw)
        self.interpolation = False

    def issubsection(self, inputCategory, sections=None, checkenabled=False):
        # checks if the inputCategory belongs to the section
        # or returns sections with subsections matching the inputCategoryu
        if not sections:
            sections = self.get_sections(inputCategory)

        if not isinstance(sections, list):
            sections = [sections]

        results = []
        for section in sections:
            if self[section].has_key(inputCategory):
                if checkenabled:
                    if self.isenabled(section, inputCategory):
                        results.append(section)
                else:
                    results.append(section)
        return results if list(set(results).intersection(set(sections))) else []

    def get_sections(self, subsections):
        # finds all sections belonging to the subsection and returns them
        if not isinstance(subsections, list):
            subsections = [subsections]

        to_return = []
        for subsection in subsections:
            for section in config().sections:
                if self[section].has_key(subsection):
                    to_return.append(section)
        return to_return

    def get_subsections(self, sections):
        # finds all subsections belonging to the section and returns them
        if not isinstance(sections, list):
            sections = [sections]

        to_return = {}
        for section in sections:
            if section in self.sections:
                for subsection in self[section].sections:
                    if not isinstance(subsection, list):
                        subsection = [subsection]
                    to_return.update({section: subsection})
        return to_return


    def isenabled(self, section, inputCategory):
        # checks if the subsection is enabled/disabled
        if int(self[section][inputCategory]['enabled']) == 1:
            return True

    def search(self, key, section, subsection=None):
        # searches for data in sections and subsections and returns it
        if subsection:
            if key in self[section][subsection].keys():
                return self[section][subsection][key]
        else:
            if key in self[section].keys():
                return self[section][key]

    def migrate(self):
        global config_new, config_old
        config_new = config_old = None

        try:
            # check for autoProcessMedia.cfg and create if it does not exist
            if not config():
                shutil.copyfile(config.SAMPLE_CONFIG_FILE, config.CONFIG_FILE)
            config_old = config()
        except:
            pass

        try:
            # check for autoProcessMedia.cfg.sample and create if it does not exist
            if not config(config.SAMPLE_CONFIG_FILE):
                shutil.copyfile(config.CONFIG_FILE, config.SAMPLE_CONFIG_FILE)
            config_new = config(config.SAMPLE_CONFIG_FILE)
        except:
            pass

        # check for autoProcessMedia.cfg and autoProcessMedia.cfg.sample and if they don't exist return and fail
        if not config() and not config(config.SAMPLE_CONFIG_FILE) or not config_new or not config_old:
            return False


        subsections = {}
        # gather all new-style and old-style sub-sections
        for newsection, newitems in config_new.iteritems():
            if config_new[newsection].sections:
                subsections.update({newsection: config_new[newsection].sections})
        for section, items in config_old.iteritems():
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
        if os.path.isfile(config.CONFIG_FILE):
            cfgbak_name = config.CONFIG_FILE + ".old"
            if os.path.isfile(cfgbak_name):  # remove older backups
                os.unlink(cfgbak_name)
            os.rename(config.CONFIG_FILE, cfgbak_name)

        # writing our configuration file to 'autoProcessMedia.cfg'
        with open(config.CONFIG_FILE, 'wb') as configFile:
            config_new.write(configFile)

        return True

    def addnzbget(self):
        config_new = config()
        section = "CouchPotato"
        envCatKey = 'NZBPO_CPSCATEGORY'
        envKeys = ['APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY', 'METHOD', 'DELETE_FAILED', 'REMOTECPS', 'WAIT_FOR', 'TIMEPERGIB']
        cfgKeys = ['apikey', 'host', 'port', 'ssl', 'web_root', 'delay', 'method', 'delete_failed', 'remoteCPS', 'wait_for', 'TimePerGiB']
        if os.environ.has_key(envCatKey):
            for index in range(len(envKeys)):
                key = 'NZBPO_CPS' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    if os.environ[envCatKey] not in config_new[section].sections:
                        config_new[section][os.environ[envCatKey]] = {}
                    config_new[section][os.environ[envCatKey]][option] = value

        section = "SickBeard"
        envCatKey = 'NZBPO_SBCATEGORY'
        envKeys = ['HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED', 'DELAY', 'TIMEPERGIB', 'PROCESS_METHOD']
        cfgKeys = ['host', 'port', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed', 'delay', 'TimePerGiB', 'process_method']
        if os.environ.has_key(envCatKey):
            for index in range(len(envKeys)):
                key = 'NZBPO_SB' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    if os.environ[envCatKey] not in config_new[section].sections:
                        config_new[section][os.environ[envCatKey]] = {}
                    config_new[section][os.environ[envCatKey]][option] = value

        section = "HeadPhones"
        envCatKey = 'NZBPO_HPCATEGORY'
        envKeys = ['APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY', 'TIMEPERGIB']
        cfgKeys = ['apikey', 'host', 'port', 'ssl', 'web_root', 'delay', 'TimePerGiB']
        if os.environ.has_key(envCatKey):
            for index in range(len(envKeys)):
                key = 'NZBPO_HP' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    if os.environ[envCatKey] not in config_new[section].sections:
                        config_new[section][os.environ[envCatKey]] = {}
                    config_new[section][os.environ[envCatKey]][option] = value

        section = "Mylar"
        envCatKey = 'NZBPO_MYCATEGORY'
        envKeys = ['HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT']
        cfgKeys = ['host', 'port', 'username', 'password', 'ssl', 'web_root']
        if os.environ.has_key(envCatKey):
            for index in range(len(envKeys)):
                key = 'NZBPO_MY' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    if os.environ[envCatKey] not in config_new[section].sections:
                        config_new[section][os.environ[envCatKey]] = {}
                    config_new[section][os.environ[envCatKey]][option] = value

        section = "Gamez"
        envCatKey = 'NZBPO_GZCATEGORY'
        envKeys = ['APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT']
        cfgKeys = ['apikey', 'host', 'port', 'ssl', 'web_root']
        if os.environ.has_key(envCatKey):
            for index in range(len(envKeys)):
                key = 'NZBPO_GZ' + envKeys[index]
                if os.environ.has_key(key):
                    option = cfgKeys[index]
                    value = os.environ[key]
                    if os.environ[envCatKey] not in config_new[section].sections:
                        config_new[section][os.environ[envCatKey]] = {}
                    config_new[section][os.environ[envCatKey]][option] = value

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
        if os.path.isfile(config.CONFIG_FILE):
            cfgbak_name = config.CONFIG_FILE + ".old"
            if os.path.isfile(cfgbak_name):  # remove older backups
                os.unlink(cfgbak_name)
            os.rename(config.CONFIG_FILE, cfgbak_name)

        # writing our configuration file to 'autoProcessMedia.cfg'
        with open(config.CONFIG_FILE, 'wb') as configFile:
            config_new.write(configFile)

lib.configobj.ConfigObj = config