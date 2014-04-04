import os
import ConfigParser

class config(object):
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

    # config error handling classes
    Error = ConfigParser.Error
    NoSectionError = ConfigParser.NoSectionError
    NoOptionError = ConfigParser.NoOptionError
    DuplicateSectionError = ConfigParser.DuplicateSectionError
    InterpolationError = ConfigParser.InterpolationError
    InterpolationMissingOptionError = ConfigParser.InterpolationMissingOptionError
    InterpolationSyntaxError = ConfigParser.InterpolationSyntaxError
    InterpolationDepthError = ConfigParser.InterpolationDepthError
    ParsingError = ConfigParser.ParsingError
    MissingSectionHeaderError = ConfigParser.MissingSectionHeaderError

    def __new__(cls, *file):
        if not file:
            file = cls.CONFIG_FILE
        return cls.loadConfig(file)

    @staticmethod
    def loadConfig(file):
        # load config
        config = ConfigParser.ConfigParser()
        config.optionxform = str
        if config.read(file):
            return config