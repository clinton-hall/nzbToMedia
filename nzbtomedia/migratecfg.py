import os
import shutil
from nzbtomedia.nzbToMediaConfig import config

class migratecfg:
    def migrate(self):
        categories = []

        # check for autoProcessMedia.cfg and autoProcessMedia.cfg.sample and if they don't exist return and fail
        if not config() and not config(config.SAMPLE_CONFIG_FILE):
            return False

        # check for autoProcessMedia.cfg and create if it does not exist
        if not config(config.CONFIG_FILE):
            shutil.copyfile(config.SAMPLE_CONFIG_FILE, config.CONFIG_FILE)
        configold = config(config.CONFIG_FILE)

        # check for autoProcessMedia.cfg.sample and create if it does not exist
        if not config(config.SAMPLE_CONFIG_FILE):
            shutil.copyfile(config.CONFIG_FILE, config.SAMPLE_CONFIG_FILE)
        confignew = config(config.SAMPLE_CONFIG_FILE)

        section = "CouchPotato"
        for option, value in configold.items(section) or config(config.MOVIE_CONFIG_FILE).items(section):
            if option == "category": # change this old format
                option = "cpsCategory"
            if option == "outputDirectory": # move this to new location format
                value = os.path.split(os.path.normpath(value))[0]
                confignew.set("Torrent", option, value)
                continue
            if option in ["username", "password" ]: # these are no-longer needed.
                continue
            if option == "cpsCategory":
                categories.extend(value.split(','))
            confignew.set(section, option, value)

        section = "SickBeard"
        for option, value in configold.items(section) or config(config.TV_CONFIG_FILE).items(section):
            if option == "category": # change this old format
                option = "sbCategory"
            if option == "wait_for": # remove old format
                continue
            if option == "failed_fork": # change this old format
                option = "fork"
                if value not in ["default", "failed", "failed-torrent", "auto"]:
                    value = "auto"
            if option == "fork" and value not in ["default", "failed", "failed-torrent", "auto"]:
                value = "auto"
            if option == "outputDirectory": # move this to new location format
                value = os.path.split(os.path.normpath(value))[0]
                confignew.set("Torrent", option, value)
                continue
            if option == "sbCategory":
                categories.extend(value.split(','))
            confignew.set(section, option, value)

        for section in configold.sections():
            try:
                for option, value in configold.items(section):
                    if section == "HeadPhones":
                        if option in ["username", "password" ]:
                            continue
                        if option == "hpCategory":
                            categories.extend(value.split(','))
                        confignew.set(section, option, value)

                    if section == "Mylar":
                        if option in "mlCategory":
                            categories.extend(value.split(','))
                        confignew.set(section, option, value)

                    if section == "Gamez":
                        if option in ["username", "password" ]: # these are no-longer needed.
                            continue
                        if option == "gzCategory":
                            categories.extend(value.split(','))
                        confignew.set(section, option, value)

                    if section == "Torrent":
                        if option in ["compressedExtensions", "mediaExtensions", "metaExtensions", "minSampleSize"]:
                            section = "Extensions" # these were moved
                        if option == "useLink": # Sym links supported now as well.
                            if isinstance(value, int):
                                num_value = int(value)
                                if num_value == 1:
                                    value = "hard"
                                else:
                                    value = "no"
                        confignew.set(section, option, value)

                    if section == "Extensions":
                        confignew.set(section, option, value)

                    if section == "Transcoder":
                        confignew.set(section, option, value)

                    if section == "WakeOnLan":
                        confignew.set(section, option, value)

                    if section == "UserScript":
                        confignew.set(section, option, value)

                    if section == "ASCII":
                        confignew.set(section, option, value)

                    if section == "passwords":
                        confignew.set(section, option, value)

                    if section == "loggers":
                        confignew.set(section, option, value)

                    if section == "handlers":
                        confignew.set(section, option, value)

                    if section == "formatters":
                        confignew.set(section, option, value)

                    if section == "logger_root":
                        confignew.set(section, option, value)

                    if section == "handler_console":
                        confignew.set(section, option, value)

                    if section == "formatter_generic":
                        confignew.set(section, option, value)
            except config.InterpolationMissingOptionError:
                pass

        for section in categories:
            try:
                if configold.items(section):
                    confignew.add_section(section)

                    for option, value in configold.items(section):
                        confignew.set(section, option, value)
            except config.NoSectionError:
                continue

        # create a backup of our old config
        if os.path.isfile(config.CONFIG_FILE):
            cfgbak_name = config.CONFIG_FILE + ".old"
            if os.path.isfile(cfgbak_name): # remove older backups
                os.unlink(cfgbak_name)
            os.rename(config.CONFIG_FILE, cfgbak_name)

        # writing our configuration file to 'autoProcessMedia.cfg'
        with open(config.CONFIG_FILE, 'wb') as configFile:
            confignew.write(configFile)

        return True

    def addnzbget(self):
        confignew = config()
        section = "CouchPotato"
        envKeys = ['CATEGORY', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY', 'METHOD', 'DELETE_FAILED', 'REMOTECPS', 'WAIT_FOR', 'TIMEPERGIB']
        cfgKeys = ['cpsCategory', 'apikey', 'host', 'port', 'ssl', 'web_root', 'delay', 'method', 'delete_failed', 'remoteCPS', 'wait_for', 'TimePerGiB']
        for index in range(len(envKeys)):
            key = 'NZBPO_CPS' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                confignew.set(section, option, value)


        section = "SickBeard"
        envKeys = ['CATEGORY', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED', 'DELAY', 'TIMEPERGIB', 'PROCESS_METHOD']
        cfgKeys = ['sbCategory', 'host', 'port', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed', 'delay', 'TimePerGiB', 'process_method']
        for index in range(len(envKeys)):
            key = 'NZBPO_SB' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                confignew.set(section, option, value)

        section = "HeadPhones"
        envKeys = ['CATEGORY', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY', 'TIMEPERGIB']
        cfgKeys = ['hpCategory', 'apikey', 'host', 'port', 'ssl', 'web_root', 'delay', 'TimePerGiB']
        for index in range(len(envKeys)):
            key = 'NZBPO_HP' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                confignew.set(section, option, value)

        section = "Mylar"
        envKeys = ['CATEGORY', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT']
        cfgKeys = ['mlCategory', 'host', 'port', 'username', 'password', 'ssl', 'web_root']
        for index in range(len(envKeys)):
            key = 'NZBPO_MY' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                confignew.set(section, option, value)

        section = "Gamez"
        envKeys = ['CATEGORY', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT']
        cfgKeys = ['gzCategory', 'apikey', 'host', 'port', 'ssl', 'web_root']
        for index in range(len(envKeys)):
            key = 'NZBPO_GZ' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                confignew.set(section, option, value)

        section = "Extensions"
        envKeys = ['COMPRESSEDEXTENSIONS', 'MEDIAEXTENSIONS', 'METAEXTENSIONS']
        cfgKeys = ['compressedExtensions', 'mediaExtensions', 'metaExtensions']
        for index in range(len(envKeys)):
            key = 'NZBPO_' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                confignew.set(section, option, value)

        section = "Transcoder"
        envKeys = ['TRANSCODE', 'DUPLICATE', 'IGNOREEXTENSIONS', 'OUTPUTVIDEOEXTENSION', 'OUTPUTVIDEOCODEC', 'OUTPUTVIDEOPRESET', 'OUTPUTVIDEOFRAMERATE', 'OUTPUTVIDEOBITRATE', 'OUTPUTAUDIOCODEC', 'OUTPUTAUDIOBITRATE', 'OUTPUTSUBTITLECODEC']
        cfgKeys = ['transcode', 'duplicate', 'ignoreExtensions', 'outputVideoExtension', 'outputVideoCodec', 'outputVideoPreset', 'outputVideoFramerate', 'outputVideoBitrate', 'outputAudioCodec', 'outputAudioBitrate', 'outputSubtitleCodec']
        for index in range(len(envKeys)):
            key = 'NZBPO_' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                confignew.set(section, option, value)

        section = "WakeOnLan"
        envKeys = ['WAKE', 'HOST', 'PORT', 'MAC']
        cfgKeys = ['wake', 'host', 'port', 'mac']
        for index in range(len(envKeys)):
            key = 'NZBPO_WOL' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                confignew.set(section, option, value)

        # create a backup of our old config
        if os.path.isfile(config.CONFIG_FILE):
            cfgbak_name = config.CONFIG_FILE + ".old"
            if os.path.isfile(cfgbak_name):  # remove older backups
                os.unlink(cfgbak_name)
            os.rename(config.CONFIG_FILE, cfgbak_name)

        # writing our configuration file to 'autoProcessMedia.cfg'
        with open(config.CONFIG_FILE, 'wb') as configFile:
            confignew.write(configFile)