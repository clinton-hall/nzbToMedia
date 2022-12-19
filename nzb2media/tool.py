from __future__ import annotations

import itertools
import logging
import os
import pathlib
import shutil
import typing

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def in_path(name: str) -> pathlib.Path | None:
    """Find tool if its on the system loc."""
    log.debug(f'Searching for {name} on system path')
    path = shutil.which(name)
    if not path:
        return None
    return pathlib.Path(path)


def at_location(root: pathlib.Path, name: str) -> pathlib.Path | None:
    """Return tool if its at given loc."""
    log.debug(f'Searching for {name} at {root}')
    if not name:
        raise ValueError('name is required')
    path = root / name
    if path.exists() or os.access(path, os.X_OK):
        return path
    return None


def find(root: pathlib.Path | None, *names) -> pathlib.Path | None:
    """Try to find a tool.

    Look in target location first, then system path,
    and finally check the current working directory.
    """
    if not names:
        raise ValueError('At least one name is required.')

    # look in target location first
    if root:
        found_at_location: typing.Iterable[pathlib.Path | None] = (at_location(root, name) for name in names)
    else:
        found_at_location = []

    # look on system path second
    found_on_path = (in_path(name) for name in names)

    found = itertools.chain(found_at_location, found_on_path)
    for path in found:
        if path is not None:
            log.info(f'Found at {path}')
            return path

    # finally check current working directory
    cwd = pathlib.Path.cwd()
    log.debug(f'Falling back on current working directory: {cwd}')

    found_in_working_directory = (at_location(cwd, name) for name in names)
    for path in found_in_working_directory:
        if path is not None:
            log.info(f'Found {path}')
            return path
    return None


def find_transcoder(root: pathlib.Path | None = None) -> pathlib.Path | None:
    """Find a tool for transcoding."""
    log.info('Searching for transcoding tool.')
    names = ('ffmpeg', 'avconv')
    found = find(root, *names)
    if not found:
        log.debug(f'Failed to locate any of the following: {names}')
        log.warning('Transcoding disabled!')
        log.warning('Install ffmpeg with x264 support to enable this feature.')
    return found


def find_video_corruption_detector(root: pathlib.Path | None = None) -> pathlib.Path | None:
    """Find a tool for detecting video corruption."""
    log.info('Searching for video corruption detection tool.')
    names = ('ffprobe', 'avprobe')
    found = find(root, *names)
    if not found:
        log.debug(f'Failed to locate any of the following: {names}')
        log.warning('Video corruption detection disabled!')
        log.warning('Install ffmpeg with x264 support to enable this feature.')
    return found


def find_archive_repairer(root: pathlib.Path | None = None) -> pathlib.Path | None:
    """Find a tool for repairing and renaming archives."""
    log.info('Searching for file repair and renaming tool.')
    names = ('par2',)
    found = find(root, *names)
    if not found:
        log.debug(f'Failed to locate any of the following: {names}')
        log.warning('Archive repair and renaming disabled!')
        log.warning('Install a parity archive repair tool to enable this feature.')
    return found


def find_unzip(root: pathlib.Path | None = None) -> pathlib.Path | None:
    """Find a tool for unzipping archives."""
    log.info('Searching for an unzipping tool.')
    names = ('7z', '7zr', '7za')
    found = find(root, *names)
    if not found:
        log.debug(f'Failed to locate any of the following: {names}')
        log.warning('Transcoding of disk images and extraction zip files will not be possible!')
    return found
