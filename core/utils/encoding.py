from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os

from six import text_type
from six import PY2

import core
from core import logger

if not PY2:
    from builtins import bytes


def char_replace(name_in):
    # Special character hex range:
    # CP850: 0x80-0xA5 (fortunately not used in ISO-8859-15)
    # UTF-8: 1st hex code 0xC2-0xC3 followed by a 2nd hex code 0xA1-0xFF
    # ISO-8859-15: 0xA6-0xFF
    # The function will detect if Name contains a special character
    # If there is special character, detects if it is a UTF-8, CP850 or ISO-8859-15 encoding
    encoded = False
    encoding = None
    if isinstance(name_in, text_type):
        return encoded, name_in
    if PY2:
        name = name_in
        for Idx in range(len(name)):
            # print('Trying to intuit the encoding')
            # /!\ detection is done 2char by 2char for UTF-8 special character
            if (len(name) != 1) & (Idx < (len(name) - 1)):
                # Detect UTF-8
                if ((name[Idx] == '\xC2') | (name[Idx] == '\xC3')) & (
                        (name[Idx + 1] >= '\xA0') & (name[Idx + 1] <= '\xFF')):
                    encoding = 'utf-8'
                    break
                # Detect CP850
                elif (name[Idx] >= '\x80') & (name[Idx] <= '\xA5'):
                    encoding = 'cp850'
                    break
                # Detect ISO-8859-15
                elif (name[Idx] >= '\xA6') & (name[Idx] <= '\xFF'):
                    encoding = 'iso-8859-15'
                    break
            else:
                # Detect CP850
                if (name[Idx] >= '\x80') & (name[Idx] <= '\xA5'):
                    encoding = 'cp850'
                    break
                # Detect ISO-8859-15
                elif (name[Idx] >= '\xA6') & (name[Idx] <= '\xFF'):
                    encoding = 'iso-8859-15'
                    break
    else:
        name = bytes(name_in)
        for Idx in range(len(name)):
            # print('Trying to intuit the encoding')
            # /!\ detection is done 2char by 2char for UTF-8 special character
            if (len(name) != 1) & (Idx < (len(name) - 1)):
                # Detect UTF-8
                if ((name[Idx] == 0xC2) | (name[Idx] == 0xC3)) & (
                        (name[Idx + 1] >= 0xA0) & (name[Idx + 1] <= 0xFF)):
                    encoding = 'utf-8'
                    break
                # Detect CP850
                elif (name[Idx] >= 0x80) & (name[Idx] <= 0xA5):
                    encoding = 'cp850'
                    break
                # Detect ISO-8859-15
                elif (name[Idx] >= 0xA6) & (name[Idx] <= 0xFF):
                    encoding = 'iso-8859-15'
                    break
            else:
                # Detect CP850
                if (name[Idx] >= 0x80) & (name[Idx] <= 0xA5):
                    encoding = 'cp850'
                    break
                # Detect ISO-8859-15
                elif (name[Idx] >= 0xA6) & (name[Idx] <= 0xFF):
                    encoding = 'iso-8859-15'
                    break
    if encoding:
        encoded = True
        name = name.decode(encoding)
    elif not PY2:
        name = name.decode()
    return encoded, name


def convert_to_ascii(input_name, dir_name):

    ascii_convert = int(core.CFG['ASCII']['convert'])
    if ascii_convert == 0 or os.name == 'nt':  # just return if we don't want to convert or on windows os and '\' is replaced!.
        return input_name, dir_name

    encoded, input_name = char_replace(input_name)

    directory, base = os.path.split(dir_name)
    if not base:  # ended with '/'
        directory, base = os.path.split(directory)

    encoded, base2 = char_replace(base)
    if encoded:
        dir_name = os.path.join(directory, base2)
        logger.info('Renaming directory to: {0}.'.format(base2), 'ENCODER')
        os.rename(os.path.join(directory, base), dir_name)
        if 'NZBOP_SCRIPTDIR' in os.environ:
            print('[NZB] DIRECTORY={0}'.format(dir_name))

    for dirname, dirnames, _ in os.walk(dir_name, topdown=False):
        for subdirname in dirnames:
            encoded, subdirname2 = char_replace(subdirname)
            if encoded:
                logger.info('Renaming directory to: {0}.'.format(subdirname2), 'ENCODER')
                os.rename(os.path.join(dirname, subdirname), os.path.join(dirname, subdirname2))

    for dirname, _, filenames in os.walk(dir_name):
        for filename in filenames:
            encoded, filename2 = char_replace(filename)
            if encoded:
                logger.info('Renaming file to: {0}.'.format(filename2), 'ENCODER')
                os.rename(os.path.join(dirname, filename), os.path.join(dirname, filename2))

    return input_name, dir_name
