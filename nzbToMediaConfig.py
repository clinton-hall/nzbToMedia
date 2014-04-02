import os
import ConfigParser

# init paths
MY_FULLNAME = os.path.normpath(os.path.abspath(__file__))
MY_NAME = os.path.basename(MY_FULLNAME)
PROG_DIR = os.path.dirname(MY_FULLNAME)

# init config file names
CONFIG_FILE = os.path.join(PROG_DIR, "autoProcessMedia.cfg")
SAMPLE_CONFIG_FILE = os.path.join(PROG_DIR, "autoProcessMedia.cfg.sample")
MOVIE_CONFIG_FILE = os.path.join(PROG_DIR, "autoProcessMovie.cfg")
TV_CONFIG_FILE = os.path.join(PROG_DIR, "autoProcessTv.cfg")
LOG_FILE = os.path.join(PROG_DIR, "postprocess.log")

class configParser(object):

    # link error handlers
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

    @staticmethod
    def config(*file):
        # if no file specified then load our default config
        if not file:file = CONFIG_FILE

        # load config
        parser = ConfigParser.ConfigParser()
        parser.optionxform = str
        if parser.read(file):return parser

config = configParser.config