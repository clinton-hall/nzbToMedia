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

class config(object):

    # link error handling classes
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
            file = CONFIG_FILE

        # load config
        config = ConfigParser.ConfigParser()
        config.optionxform = str
        if config.read(file):
            return config