#System imports
import ConfigParser
import sys
import os

def migrate():
    confignew = ConfigParser.ConfigParser()
    confignew.optionxform = str
    configFilenamenew = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.sample")
    confignew.read(configFilenamenew)

    configold = ConfigParser.ConfigParser()
    configold.optionxform = str

    categories = []

    section = "CouchPotato"
    original = []
    configFilenameold = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    if not os.path.isfile(configFilenameold): # lets look back for an older version.
        configFilenameold = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMovie.cfg")
        if not os.path.isfile(configFilenameold): # no config available
            configFilenameold = ""
    if configFilenameold: # read our old config.
        configold.read(configFilenameold)
        try:
            original = configold.items(section)
        except:
            pass
    for item in original:
        option, value = item
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
    original = []
    configFilenameold = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    if not os.path.isfile(configFilenameold): # lets look back for an older version.
        configFilenameold = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessTV.cfg")
        if not os.path.isfile(configFilenameold): # no config available
            configFilenameold = ""
    if configFilenameold: # read our old config.
        configold.read(configFilenameold)
        try:
            original = configold.items(section)
        except:
            pass
    for item in original:
        option, value = item
        if option == "category": # change this old format
            option = "sbCategory"
        if option == "failed_fork": # change this old format
            option = "fork"
            if int(value) == 1:
                value = "failed"
            else:
                value = "default"
        if option == "outputDirectory": # move this to new location format
            value = os.path.split(os.path.normpath(value))[0]
            confignew.set("Torrent", option, value)
            continue
        if option == "sbCategory":
            categories.extend(value.split(','))
        confignew.set(section, option, value) 

    section = "HeadPhones"
    original = []
    configFilenameold = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    if os.path.isfile(configFilenameold): # read our old config.
        configold.read(configFilenameold)
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        if option in ["username", "password" ]: # these are no-longer needed.
            continue
        option, value = item
        if option == "hpCategory":
            categories.extend(value.split(','))
        confignew.set(section, option, value) 

    section = "Mylar"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        if option == "mlCategory":
            categories.extend(value.split(','))
        confignew.set(section, option, value)

    section = "Gamez"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        if option in ["username", "password" ]: # these are no-longer needed.
            continue
        if option == "gzCategory":
            categories.extend(value.split(','))
        confignew.set(section, option, value)

    for section in categories:
        original = []
        try:
            original = configold.items(section)
        except:
            continue
        for item in original:
            option, value = item
            confignew.set(section, option, value) 

    section = "Torrent"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        if option in ["compressedExtensions", "mediaExtensions", "metaExtensions", "minSampleSize"]:
            section = "Extensions" # these were moved
        if option == "useLink": # Sym links supported now as well.
            try:
                num_value = int(value)
                if num_value == 1:
                    value = "hard"
                else:
                    value = "no"
            except ValueError:
                pass
        confignew.set(section, option, value)
        section = "Torrent" # reset in case extensions out of order.

    section = "Extensions"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "Transcoder"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "WakeOnLan"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "UserScript"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "ASCII"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "passwords"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "loggers"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "handlers"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "formatters"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "logger_root"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "handler_console"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "formatter_generic"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    # writing our configuration file to 'autoProcessMedia.cfg.sample'
    with open(configFilenamenew, 'wb') as configFile:
        confignew.write(configFile)

    # create a backup of our old config
    if os.path.isfile(configFilenameold):
        backupname = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.old")
        if os.path.isfile(backupname): # remove older backups
            os.unlink(backupname)
        os.rename(configFilenameold, backupname)

    if os.path.isfile(configFilenamenew):
        # rename our newly edited autoProcessMedia.cfg.sample to autoProcessMedia.cfg
        os.rename(configFilenamenew, configFilenameold)
        return

def addnzbget():
    confignew = ConfigParser.ConfigParser()
    confignew.optionxform = str
    configFilenamenew = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    confignew.read(configFilenamenew)

    section = "CouchPotato"
    envKeys = ['CATEGORY', 'APIKEY', 'HOST', 'PORT', 'SSL', 'WEB_ROOT', 'DELAY', 'METHOD', 'DELETE_FAILED', 'REMOTECPS']
    cfgKeys = ['cpsCategory', 'apikey', 'host', 'port', 'ssl', 'web_root', 'delay', 'method', 'delete_failed', 'remoteCPS']
    for index in range(len(envKeys)):
        key = 'NZBPO_CPS' + envKeys[index]
        if os.environ.has_key(key):
            option = cfgKeys[index]
            value = os.environ[key]
            confignew.set(section, option, value)


    section = "SickBeard"
    envKeys = ['CATEGORY', 'HOST', 'PORT', 'USERNAME', 'PASSWORD', 'SSL', 'WEB_ROOT', 'WATCH_DIR', 'FORK']
    cfgKeys = ['sbCategory', 'host', 'port', 'username', 'password', 'ssl', 'web_root', 'watch_dir', 'fork']
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
        key = 'NZBPO_ML' + envKeys[index]
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
    with open(configFilenamenew, 'wb') as configFile:
        confignew.write(configFile)

    return
