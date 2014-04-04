import os
import shutil
from nzbtomedia.nzbToMediaConfig import config
from itertools import chain

class migratecfg:
    def migrate(self):
        categories = {}
        confignew = None
        configold = None

        try:
            # check for autoProcessMedia.cfg and create if it does not exist
            if not config(config.CONFIG_FILE):
                shutil.copyfile(config.SAMPLE_CONFIG_FILE, config.CONFIG_FILE)
            configold = config(config.CONFIG_FILE)
        except:pass

        try:
            # check for autoProcessMedia.cfg.sample and create if it does not exist
            if not config(config.SAMPLE_CONFIG_FILE):
                shutil.copyfile(config.CONFIG_FILE, config.SAMPLE_CONFIG_FILE)
            confignew = config(config.SAMPLE_CONFIG_FILE)
        except:pass

        # check for autoProcessMedia.cfg and autoProcessMedia.cfg.sample and if they don't exist return and fail
        if not config() and not config(config.SAMPLE_CONFIG_FILE) or not confignew or not configold:
            return False

        for section in configold.sections:
            for option, value in configold[section].items():
                if section == "CouchPotato":
                    if option == "category":  # change this old format
                        option = "cpsCategory"
                if section == "SickBeard":
                    if option == "category":  # change this old format
                        option = "sbCategory"
                if option in ["cpsCategory","sbCategory","hpCategory","mlCategory","gzCategory"]:
                    if not isinstance(value, list):
                        value = [value]

                    categories.update({section: value})
                    continue

        try:
            for section in configold.sections:
                subsection = None
                if section in list(chain.from_iterable(categories.values())):
                    subsection = section
                    section = ''.join([k for k, v in categories.iteritems() if subsection in v])
                elif section in categories.keys():
                    subsection = categories[section][0]

                # create subsection if it does not exist
                if subsection and subsection not in confignew[section].sections:
                    confignew[section][subsection] = {}

                for option, value in configold[section].items():
                    if section == "CouchPotato":
                        if option == "outputDirectory":  # move this to new location format
                            value = os.path.split(os.path.normpath(value))[0]
                            confignew['Torrent'][option] = value
                            continue
                        if option in ["username", "password"]:  # these are no-longer needed.
                            continue
                        if option in ["category","cpsCategory"]:
                            continue

                    if section == "SickBeard":
                        if option == "wait_for":  # remove old format
                            continue
                        if option == "failed_fork":  # change this old format
                            option = "fork"
                            value = "auto"
                        if option == "Torrent_ForceLink":
                            continue
                        if option == "outputDirectory":  # move this to new location format
                            value = os.path.split(os.path.normpath(value))[0]
                            confignew['Torrent'][option] = value
                            continue
                        if option in ["category", "sbCategory"]:
                            continue

                    if section == "HeadPhones":
                        if option in ["username", "password" ]:
                            continue
                        if option == "hpCategory":
                            continue

                    if section == "Mylar":
                        if option in "mlCategory":
                            continue

                    if section == "Gamez":
                        if option in ["username", "password"]:  # these are no-longer needed.
                            continue
                        if option == "gzCategory":
                            continue

                    if section == "Torrent":
                        if option in ["compressedExtensions", "mediaExtensions", "metaExtensions", "minSampleSize"]:
                            section = "Extensions"  # these were moved
                        if option == "useLink":  # Sym links supported now as well.
                            if isinstance(value, int):
                                num_value = int(value)
                                if num_value == 1:
                                    value = "hard"
                                else:
                                    value = "no"

                    if subsection:
                        confignew[section][subsection][option] = value
                    else:
                        confignew[section][option] = value
        except:pass

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
        envCatKey = 'NZBPO_CPSCATEGORY'
        envKeys = ['APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY', 'METHOD', 'DELETE_FAILED', 'REMOTECPS', 'WAIT_FOR', 'TIMEPERGIB']
        cfgKeys = ['apikey', 'host', 'port', 'ssl', 'web_root', 'delay', 'method', 'delete_failed', 'remoteCPS', 'wait_for', 'TimePerGiB']
        for index in range(len(envKeys)):
            key = 'NZBPO_CPS' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                if confignew[section].has_key(os.environ[envCatKey]) and option not in confignew[section].sections:
                    confignew[section][envCatKey][option] = value


        section = "SickBeard"
        envCatKey = 'NZBPO_SBCATEGORY'
        envKeys = ['HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED', 'DELAY', 'TIMEPERGIB', 'PROCESS_METHOD']
        cfgKeys = ['host', 'port', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed', 'delay', 'TimePerGiB', 'process_method']
        for index in range(len(envKeys)):
            key = 'NZBPO_SB' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                if confignew[section].has_key(os.environ[envCatKey]) and option not in confignew[section].sections:
                    confignew[section][envCatKey][option] = value

        section = "HeadPhones"
        envCatKey = 'NZBPO_HPCATEGORY'
        envKeys = ['APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY', 'TIMEPERGIB']
        cfgKeys = ['apikey', 'host', 'port', 'ssl', 'web_root', 'delay', 'TimePerGiB']
        for index in range(len(envKeys)):
            key = 'NZBPO_HP' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                if confignew[section].has_key(os.environ[envCatKey]) and option not in confignew[section].sections:
                    confignew[section][envCatKey][option] = value

        section = "Mylar"
        envCatKey = 'NZBPO_MYCATEGORY'
        envKeys = ['HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT']
        cfgKeys = ['host', 'port', 'username', 'password', 'ssl', 'web_root']
        for index in range(len(envKeys)):
            key = 'NZBPO_MY' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                if confignew[section].has_key(os.environ[envCatKey]) and option not in confignew[section].sections:
                    confignew[section][envCatKey][option] = value

        section = "Gamez"
        envCatKey = 'NZBPO_GZCATEGORY'
        envKeys = ['APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT']
        cfgKeys = ['apikey', 'host', 'port', 'ssl', 'web_root']
        for index in range(len(envKeys)):
            key = 'NZBPO_GZ' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                if confignew[section].has_key(os.environ[envCatKey]) and option not in confignew[section].sections:
                    confignew[section][envCatKey][option] = value

        section = "Extensions"
        envKeys = ['COMPRESSEDEXTENSIONS', 'MEDIAEXTENSIONS', 'METAEXTENSIONS']
        cfgKeys = ['compressedExtensions', 'mediaExtensions', 'metaExtensions']
        for index in range(len(envKeys)):
            key = 'NZBPO_' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                confignew[section][option] = value

        section = "Transcoder"
        envKeys = ['TRANSCODE', 'DUPLICATE', 'IGNOREEXTENSIONS', 'OUTPUTVIDEOEXTENSION', 'OUTPUTVIDEOCODEC', 'OUTPUTVIDEOPRESET', 'OUTPUTVIDEOFRAMERATE', 'OUTPUTVIDEOBITRATE', 'OUTPUTAUDIOCODEC', 'OUTPUTAUDIOBITRATE', 'OUTPUTSUBTITLECODEC']
        cfgKeys = ['transcode', 'duplicate', 'ignoreExtensions', 'outputVideoExtension', 'outputVideoCodec', 'outputVideoPreset', 'outputVideoFramerate', 'outputVideoBitrate', 'outputAudioCodec', 'outputAudioBitrate', 'outputSubtitleCodec']
        for index in range(len(envKeys)):
            key = 'NZBPO_' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                confignew[section][option] = value

        section = "WakeOnLan"
        envKeys = ['WAKE', 'HOST', 'PORT', 'MAC']
        cfgKeys = ['wake', 'host', 'port', 'mac']
        for index in range(len(envKeys)):
            key = 'NZBPO_WOL' + envKeys[index]
            if os.environ.has_key(key):
                option = cfgKeys[index]
                value = os.environ[key]
                confignew[section][option] = value

        # create a backup of our old config
        if os.path.isfile(config.CONFIG_FILE):
            cfgbak_name = config.CONFIG_FILE + ".old"
            if os.path.isfile(cfgbak_name):  # remove older backups
                os.unlink(cfgbak_name)
            os.rename(config.CONFIG_FILE, cfgbak_name)

        # writing our configuration file to 'autoProcessMedia.cfg'
        with open(config.CONFIG_FILE, 'wb') as configFile:
            confignew.write(configFile)