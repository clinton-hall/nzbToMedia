from __future__ import annotations

import logging
import os
import re
import shutil
import stat
import time

import guessit
import mediafile

import nzb2media
from nzb2media import extractor
from nzb2media.utils.links import copy_link
from nzb2media.utils.naming import is_sample
from nzb2media.utils.naming import sanitize_name
from nzb2media.utils.paths import get_dir_size
from nzb2media.utils.paths import make_dir

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def move_file(filename, path, link):
    log.debug(f'Found file {os.path.split(filename)[1]} in root directory {path}.')
    new_path = None
    file_ext = os.path.splitext(filename)[1]
    try:
        if file_ext in nzb2media.AUDIO_CONTAINER:
            f = mediafile.MediaFile(filename)

            # get artist and album info
            artist = f.artist
            album = f.album

            # create new path
            new_path = os.path.join(
                path, f'{sanitize_name(artist)} - {sanitize_name(album)}',
            )
        elif file_ext in nzb2media.MEDIA_CONTAINER:
            f = guessit.guessit(filename)

            # get title
            title = f.get('series') or f.get('title')

            if not title:
                title = os.path.splitext(os.path.basename(filename))[0]

            new_path = os.path.join(path, sanitize_name(title))
    except Exception as error:
        log.error(f'Exception parsing name for media file: {os.path.split(filename)[1]}: {error}')

    if not new_path:
        title = os.path.splitext(os.path.basename(filename))[0]
        new_path = os.path.join(path, sanitize_name(title))

    # # Removed as encoding of directory no-longer required
    # try:
    #     new_path = new_path.encode(nzb2media.SYS_ENCODING)
    # except Exception:
    #     pass

    # Just fail-safe incase we already have afile with this clean-name (was actually a bug from earlier code, but let's be safe).
    if os.path.isfile(new_path):
        new_path2 = os.path.join(
            os.path.join(os.path.split(new_path)[0], 'new'),
            os.path.split(new_path)[1],
        )
        new_path = new_path2

    # create new path if it does not exist
    if not os.path.exists(new_path):
        make_dir(new_path)

    newfile = os.path.join(
        new_path, sanitize_name(os.path.split(filename)[1]),
    )
    try:
        newfile = newfile.encode(nzb2media.SYS_ENCODING)
    except Exception:
        pass

    # link file to its new path
    copy_link(filename, newfile, link)


def is_min_size(input_name, min_size):
    file_name, file_ext = os.path.splitext(os.path.basename(input_name))

    # audio files we need to check directory size not file size
    input_size = os.path.getsize(input_name)
    if file_ext in nzb2media.AUDIO_CONTAINER:
        try:
            input_size = get_dir_size(os.path.dirname(input_name))
        except Exception:
            log.error(f'Failed to get file size for {input_name}')
            return True

    # Ignore files under a certain size
    if input_size > min_size * 1048576:
        return True


def is_archive_file(filename):
    """Check if the filename is allowed for the Archive."""
    for regext in nzb2media.COMPRESSED_CONTAINER:
        if regext.search(filename):
            return regext.split(filename)[0]
    return False


def is_media_file(
    mediafile,
    media=True,
    audio=True,
    meta=True,
    archives=True,
    other=False,
    otherext=None,
):
    if otherext is None:
        otherext = []

    file_name, file_ext = os.path.splitext(mediafile)

    try:
        # ignore MAC OS's 'resource fork' files
        if file_name.startswith('._'):
            return False
    except Exception:
        pass

    return any(
        [
            (media and file_ext.lower() in nzb2media.MEDIA_CONTAINER),
            (audio and file_ext.lower() in nzb2media.AUDIO_CONTAINER),
            (meta and file_ext.lower() in nzb2media.META_CONTAINER),
            (archives and is_archive_file(mediafile)),
            (other and (file_ext.lower() in otherext or 'all' in otherext)),
        ],
    )


def list_media_files(
    path,
    min_size=0,
    delete_ignored=0,
    media=True,
    audio=True,
    meta=True,
    archives=True,
    other=False,
    otherext=None,
):
    if otherext is None:
        otherext = []

    files = []
    if not os.path.isdir(path):
        if os.path.isfile(path):  # Single file downloads.
            cur_file = os.path.split(path)[1]
            if is_media_file(
                cur_file, media, audio, meta, archives, other, otherext,
            ):
                # Optionally ignore sample files
                if is_sample(path) or not is_min_size(path, min_size):
                    if delete_ignored == 1:
                        try:
                            os.unlink(path)
                            log.debug(f'Ignored file {cur_file} has been removed ...')
                        except Exception:
                            pass
                else:
                    files.append(path)

        return files

    for cur_file in os.listdir(path):
        full_cur_file = os.path.join(path, cur_file)

        # if it's a folder do it recursively
        if os.path.isdir(full_cur_file) and not cur_file.startswith('.'):
            files += list_media_files(
                full_cur_file,
                min_size,
                delete_ignored,
                media,
                audio,
                meta,
                archives,
                other,
                otherext,
            )

        elif is_media_file(
            cur_file, media, audio, meta, archives, other, otherext,
        ):
            # Optionally ignore sample files
            if is_sample(full_cur_file) or not is_min_size(
                full_cur_file, min_size,
            ):
                if delete_ignored == 1:
                    try:
                        os.unlink(full_cur_file)
                        log.debug(f'Ignored file {cur_file} has been removed ...')
                    except Exception:
                        pass
                continue

            files.append(full_cur_file)

    return sorted(files, key=len)


def extract_files(src, dst=None, keep_archive=None):
    extracted_folder = []
    extracted_archive = []

    for inputFile in list_media_files(
        src, media=False, audio=False, meta=False, archives=True,
    ):
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
            log.error(f'Extraction failed for: {full_file_name}')

    for folder in extracted_folder:
        for inputFile in list_media_files(
            folder, media=False, audio=False, meta=False, archives=True,
        ):
            full_file_name = os.path.basename(inputFile)
            archive_name = os.path.splitext(full_file_name)[0]
            archive_name = re.sub(r'part[0-9]+', '', archive_name)
            if archive_name not in extracted_archive or keep_archive:
                continue  # don't remove if we haven't extracted this archive, or if we want to preserve them.
            log.info(f'Removing extracted archive {full_file_name} from folder {folder} ...')
            try:
                if not os.access(inputFile, os.W_OK):
                    os.chmod(inputFile, stat.S_IWUSR)
                os.remove(inputFile)
                time.sleep(1)
            except Exception as error:
                log.error(f'Unable to remove file {inputFile} due to: {error}')


def backup_versioned_file(old_file, version):
    num_tries = 0
    new_file = f'{old_file}.v{version}'
    while not os.path.isfile(new_file):
        if not os.path.isfile(old_file):
            log.debug(f'Not creating backup, {old_file} doesn\'t exist')
            break
        try:
            log.debug(f'Trying to back up {old_file} to {new_file}')
            shutil.copy(old_file, new_file)
            log.debug('Backup done')
            break
        except Exception as error:
            log.warning(f'Error while trying to back up {old_file} to {new_file} : {error}')
            num_tries += 1
            time.sleep(1)
            log.debug('Trying again.')
        if num_tries >= 10:
            log.error(f'Unable to back up {old_file} to {new_file} please do it manually.')
            return False
    return True
