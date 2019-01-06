import shutil
import os
import re
import stat
import time

from six import text_type

import core
from core import extractor, logger
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

    return any([
        (media and file_ext.lower() in core.MEDIACONTAINER),
        (audio and file_ext.lower() in core.AUDIOCONTAINER),
        (meta and file_ext.lower() in core.METACONTAINER),
        (archives and is_archive_file(mediafile)),
        (other and (file_ext.lower() in otherext or 'all' in otherext)),
    ])


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


def extract_files(src, dst=None, keep_archive=None):
    extracted_folder = []
    extracted_archive = []

    for inputFile in list_media_files(src, media=False, audio=False, meta=False, archives=True):
        dir_path = os.path.dirname(inputFile)
        full_file_name = os.path.basename(inputFile)
        archive_name = os.path.splitext(full_file_name)[0]
        archive_name = re.sub(r'part[0-9]+', '', archive_name)

        if dir_path in extracted_folder and archive_name in extracted_archive:
            continue  # no need to extract this, but keep going to look for other archives and sub directories.

        try:
            if extractor.extract(inputFile, dst or dir_path):
                extracted_folder.append(dir_path)
                extracted_archive.append(archive_name)
        except Exception:
            logger.error('Extraction failed for: {0}'.format(full_file_name))

    for folder in extracted_folder:
        for inputFile in list_media_files(folder, media=False, audio=False, meta=False, archives=True):
            full_file_name = os.path.basename(inputFile)
            archive_name = os.path.splitext(full_file_name)[0]
            archive_name = re.sub(r'part[0-9]+', '', archive_name)
            if archive_name not in extracted_archive or keep_archive:
                continue  # don't remove if we haven't extracted this archive, or if we want to preserve them.
            logger.info('Removing extracted archive {0} from folder {1} ...'.format(full_file_name, folder))
            try:
                if not os.access(inputFile, os.W_OK):
                    os.chmod(inputFile, stat.S_IWUSR)
                os.remove(inputFile)
                time.sleep(1)
            except Exception as e:
                logger.error('Unable to remove file {0} due to: {1}'.format(inputFile, e))


def backup_versioned_file(old_file, version):
    num_tries = 0

    new_file = '{old}.v{version}'.format(old=old_file, version=version)

    while not os.path.isfile(new_file):
        if not os.path.isfile(old_file):
            logger.log(u'Not creating backup, {file} doesn\'t exist'.format(file=old_file), logger.DEBUG)
            break

        try:
            logger.log(u'Trying to back up {old} to {new]'.format(old=old_file, new=new_file), logger.DEBUG)
            shutil.copy(old_file, new_file)
            logger.log(u'Backup done', logger.DEBUG)
            break
        except Exception as error:
            logger.log(u'Error while trying to back up {old} to {new} : {msg}'.format
                       (old=old_file, new=new_file, msg=error), logger.WARNING)
            num_tries += 1
            time.sleep(1)
            logger.log(u'Trying again.', logger.DEBUG)

        if num_tries >= 10:
            logger.log(u'Unable to back up {old} to {new} please do it manually.'.format(old=old_file, new=new_file), logger.ERROR)
            return False

    return True
