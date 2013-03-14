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
            value = os.path.split(os.path.normpath(outputdirectory))[0]
            confignew.set("Torrent", option, value)
            continue
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
        if option == "outputDirectory": # move this to new location format
            value = os.path.split(os.path.normpath(outputdirectory))[0]
            confignew.set("Torrent", option, value)
            continue
        confignew.set(section, option, value) 

    section = "HeadPhones"
    original = []
    configFilenameold = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg")
    if not os.path.isfile(configFilenameold):
        configFilenameold = ""
    if configFilenameold: # read our old config.
        configold.read(configFilenameold)
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value) 

    section = "Mylar"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
    for item in original:
        option, value = item
        confignew.set(section, option, value)

    section = "Gamez"
    original = []
    try:
        original = configold.items(section)
    except:
        pass
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
        if option in ["compressedExtensions", "mediaExtensions", "metaExtensions"]:
            section = "Extensions" # these were moved
        confignew.set(section, option, value)
        section = "Torrent" # reset in case extensions out of order.

    section = "Transcoder"
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
    backupname = os.path.join(os.path.dirname(sys.argv[0]), "autoProcessMedia.cfg.old")
    if os.path.isfile(backupname): # remove older backups
        os.unlink(backupname)
    os.rename(configFilenameold, backupname)

    # rename our newly edited autoProcessMedia.cfg.sample to autoProcessMedia.cfg
    os.rename(configFilenamenew, configFilenameold)
    return
