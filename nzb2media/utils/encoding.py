from __future__ import annotations

import logging
import os

import nzb2media

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def char_replace(name_in):
    # Special character hex range:
    # CP850: 0x80-0xA5 (fortunately not used in ISO-8859-15)
    # UTF-8: 1st hex code 0xC2-0xC3 followed by a 2nd hex code 0xA1-0xFF
    # ISO-8859-15: 0xA6-0xFF
    # The function will detect if Name contains a special character
    # If there is special character, detects if it is a UTF-8, CP850 or ISO-8859-15 encoding
    encoded = False
    encoding = None
    if isinstance(name_in, str):
        return encoded, name_in
    name = bytes(name_in)
    for Idx in range(len(name)):
        # print('Trying to intuit the encoding')
        # /!\ detection is done 2char by 2char for UTF-8 special character
        if (len(name) != 1) & (Idx < (len(name) - 1)):
            # Detect UTF-8
            if ((name[Idx] == 0xC2) | (name[Idx] == 0xC3)) & (
                (name[Idx + 1] >= 0xA0) & (name[Idx + 1] <= 0xFF)
            ):
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
    else:
        name = name.decode()
    return encoded, name


def convert_to_ascii(input_name, dir_name):

    ascii_convert = int(nzb2media.CFG['ASCII']['convert'])
    if (
        ascii_convert == 0 or os.name == 'nt'
    ):  # just return if we don't want to convert or on windows os and '\' is replaced!.
        return input_name, dir_name

    encoded, input_name = char_replace(input_name)

    directory, base = os.path.split(dir_name)
    if not base:  # ended with '/'
        directory, base = os.path.split(directory)

    encoded, base2 = char_replace(base)
    if encoded:
        dir_name = os.path.join(directory, base2)
        log.info(f'Renaming directory to: {base2}.')
        os.rename(os.path.join(directory, base), dir_name)
        if 'NZBOP_SCRIPTDIR' in os.environ:
            print(f'[NZB] DIRECTORY={dir_name}')

    for dirname, dirnames, _ in os.walk(dir_name, topdown=False):
        for subdirname in dirnames:
            encoded, subdirname2 = char_replace(subdirname)
            if encoded:
                log.info(f'Renaming directory to: {subdirname2}.')
                os.rename(
                    os.path.join(dirname, subdirname),
                    os.path.join(dirname, subdirname2),
                )

    for dirname, _, filenames in os.walk(dir_name):
        for filename in filenames:
            encoded, filename2 = char_replace(filename)
            if encoded:
                log.info(f'Renaming file to: {filename2}.')
                os.rename(
                    os.path.join(dirname, filename),
                    os.path.join(dirname, filename2),
                )

    return input_name, dir_name
