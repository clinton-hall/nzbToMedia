from nzbToMediaConfig import *

def migrate():
    categories = []
    confignew = config(SAMPLE_CONFIG_FILE)
    configold = config(CONFIG_FILE)

    section = "CouchPotato"
    for option, value in configold.items(section) or config(MOVIE_CONFIG_FILE).items(section):
        if option is "category": # change this old format
            option = "cpsCategory"
        if option is "outputDirectory": # move this to new location format
            value = os.path.split(os.path.normpath(value))[0]
            confignew.set("Torrent", option, value)
            continue
        if option in ["username", "password" ]: # these are no-longer needed.
            continue
        if option is "cpsCategory":
            categories.extend(value.split(','))
        confignew.set(section, option, value)

    section = "SickBeard"
    for option, value in configold.items(section) or config(TV_CONFIG_FILE).items(section):
        if option is "category": # change this old format
            option = "sbCategory"
        if option is "failed_fork": # change this old format
            option = "fork"
            if value not in ["default", "failed", "failed-torrent", "auto"]:
                value = "auto"
        if option is "fork" and value not in ["default", "failed", "failed-torrent", "auto"]:
            value = "auto"
        if option is "outputDirectory": # move this to new location format
            value = os.path.split(os.path.normpath(value))[0]
            confignew.set("Torrent", option, value)
            continue
        if option is "sbCategory":
            categories.extend(value.split(','))
        confignew.set(section, option, value) 

    for section in configold.sections():
        if section is "HeadPhones":
            if option in ["username", "password" ]:
                continue
            if option is "hpCategory":
                categories.extend(value.split(','))
            confignew.set(section, option, value)

        if section is "Mylar":
            if option in "mlCategory":
                categories.extend(value.split(','))
            confignew.set(section, option, value)

        if section is "Gamez":
            if option in ["username", "password" ]: # these are no-longer needed.
                continue
            if option == "gzCategory":
                categories.extend(value.split(','))
            confignew.set(section, option, value)

        if section is "Torrent":
            if option in ["compressedExtensions", "mediaExtensions", "metaExtensions", "minSampleSize"]:
                section = "Extensions" # these were moved
            if option is "useLink": # Sym links supported now as well.
                num_value = int(value or 0)
                if num_value is 1:
                    value = "hard"
                else:
                    value = "no"
            confignew.set(section, option, value)

        if section is "Extensions":
            confignew.set(section, option, value)

        if section is "Transcoder":
            confignew.set(section, option, value)

        if section is "WakeOnLan":
            confignew.set(section, option, value)

        if section is "UserScript":
            confignew.set(section, option, value)

        if section is "ASCII":
            confignew.set(section, option, value)

        if section is "passwords":
            confignew.set(section, option, value)

        if section is "loggers":
            confignew.set(section, option, value)

        if section is "handlers":
            confignew.set(section, option, value)

        if section is "formatters":
            confignew.set(section, option, value)

        if section is "logger_root":
            confignew.set(section, option, value)

        if section is "handler_console":
            confignew.set(section, option, value)

        if section is "formatter_generic":
            confignew.set(section, option, value)

    for section in categories:
        if configold.items(section):
            confignew.add_section(section)

            for option, value in configold.items(section):
                confignew.set(section, option, value)

    # create a backup of our old config
    if os.path.isfile(CONFIG_FILE):
        cfgbak_name = CONFIG_FILE + ".old"
        if os.path.isfile(cfgbak_name): # remove older backups
            os.unlink(cfgbak_name)
        os.rename(CONFIG_FILE, cfgbak_name)

    # writing our configuration file to 'autoProcessMedia.cfg.sample'
    with open(CONFIG_FILE, 'wb') as configFile:
        confignew.write(configFile)

def addnzbget():
    confignew = config()
    section = "CouchPotato"
    envKeys = ['CATEGORY', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY', 'METHOD', 'DELETE_FAILED', 'REMOTECPS', 'WAIT_FOR']
    cfgKeys = ['cpsCategory', 'apikey', 'host', 'port', 'ssl', 'web_root', 'delay', 'method', 'delete_failed', 'remoteCPS', 'wait_for']
    for index in range(len(envKeys)):
        key = 'NZBPO_CPS' + envKeys[index]
        if os.environ.has_key(key):
            option = cfgKeys[index]
            value = os.environ[key]
            confignew.set(section, option, value)


    section = "SickBeard"
    envKeys = ['CATEGORY', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK', 'DELETE_FAILED', 'DELAY', 'WAIT_FOR', 'PROCESS_METHOD']
    cfgKeys = ['sbCategory', 'host', 'port', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork', 'delete_failed', 'delay', 'wait_for', 'process_method']
    for index in range(len(envKeys)):
        key = 'NZBPO_SB' + envKeys[index]
        if os.environ.has_key(key):
            option = cfgKeys[index]
            value = os.environ[key]
            confignew.set(section, option, value)

    section = "HeadPhones"
    envKeys = ['CATEGORY', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY']
    cfgKeys = ['hpCategory', 'apikey', 'host', 'port', 'ssl', 'web_root', 'delay']
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

    # writing our configuration file to 'autoProcessMedia.cfg'
    with open(CONFIG_FILE, 'wb') as configFile:
        confignew.write(configFile)