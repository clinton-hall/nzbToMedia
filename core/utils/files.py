import os

from six import text_type

import core
from core import logger
from core.utils.naming import is_sample
from core.utils.paths import get_dir_size


def is_min_size(input_name, min_size):
    file_name, file_ext = os.path.splitext(os.path.basename(input_name))

    # audio files we need to check directory size not file size
    input_size = os.path.getsize(input_name)
    if file_ext in core.AUDIOCONTAINER:
        try:
            input_size = get_dir_size(os.path.dirname(input_name))
        except Exception:
            logger.error('Failed to get file size for {0}'.format(input_name), 'MINSIZE')
            return True

    # Ignore files under a certain size
    if input_size > min_size * 1048576:
        return True


def is_archive_file(filename):
    """Check if the filename is allowed for the Archive"""
    for regext in core.COMPRESSEDCONTAINER:
        if regext.search(filename):
            return regext.split(filename)[0]
    return False


def is_media_file(mediafile, media=True, audio=True, meta=True, archives=True, other=False, otherext=None):
    if otherext is None:
        otherext = []

    file_name, file_ext = os.path.splitext(mediafile)

    try:
        # ignore MAC OS's 'resource fork' files
        if file_name.startswith('._'):
            return False
    except Exception:
        pass
    if (media and file_ext.lower() in core.MEDIACONTAINER) \
            or (audio and file_ext.lower() in core.AUDIOCONTAINER) \
            or (meta and file_ext.lower() in core.METACONTAINER) \
            or (archives and is_archive_file(mediafile)) \
            or (other and (file_ext.lower() in otherext or 'all' in otherext)):
        return True
    else:
        return False


def list_media_files(path, min_size=0, delete_ignored=0, media=True, audio=True, meta=True, archives=True, other=False, otherext=None):
    if otherext is None:
        otherext = []

    files = []
    if not os.path.isdir(path):
        if os.path.isfile(path):  # Single file downloads.
            cur_file = os.path.split(path)[1]
            if is_media_file(cur_file, media, audio, meta, archives, other, otherext):
                # Optionally ignore sample files
                if is_sample(path) or not is_min_size(path, min_size):
                    if delete_ignored == 1:
                        try:
                            os.unlink(path)
                            logger.debug('Ignored file {0} has been removed ...'.format
                                         (cur_file))
                        except Exception:
                            pass
                else:
                    files.append(path)

        return files

    for cur_file in os.listdir(text_type(path)):
        full_cur_file = os.path.join(path, cur_file)

        # if it's a folder do it recursively
        if os.path.isdir(full_cur_file) and not cur_file.startswith('.'):
            files += list_media_files(full_cur_file, min_size, delete_ignored, media, audio, meta, archives, other, otherext)

        elif is_media_file(cur_file, media, audio, meta, archives, other, otherext):
            # Optionally ignore sample files
            if is_sample(full_cur_file) or not is_min_size(full_cur_file, min_size):
                if delete_ignored == 1:
                    try:
                        os.unlink(full_cur_file)
                        logger.debug('Ignored file {0} has been removed ...'.format
                                     (cur_file))
                    except Exception:
                        pass
                continue

            files.append(full_cur_file)

    return sorted(files, key=len)
