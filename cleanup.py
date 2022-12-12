#!/usr/bin/env python

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
import subprocess
import sys
import shutil

sys.dont_write_bytecode = True

FOLDER_STRUCTURE = {
    'libs': [
        'common',
        'custom',
        'py2',
        'win',
    ],
    'core': [
        'auto_process',
        'extractor',
        'plugins',
        'processor',
        'utils',
    ],
}


class WorkingDirectory(object):
    """Context manager for changing current working directory."""

    def __init__(self, new, original=None):
        self.working_directory = new
        self.original_directory = os.getcwd() if original is None else original

    def __enter__(self):
        os.chdir(self.working_directory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            os.chdir(self.original_directory)
        except OSError as error:
            print(
                'Unable to return to {original_directory}: {error}\n'
                'Continuing in {working_directory}'.format(
                    original_directory=self.original_directory,
                    error=error,
                    working_directory=self.working_directory,
                ),
            )


def module_path(module=__file__, parent=False):
    """
    Detect path for a module.

    :param module: The module who's path is being detected.  Defaults to current module.
    :param parent: True to return the parent folder of the current module.
    :return: The absolute normalized path to the module or its parent.
    """
    try:
        path = module.__file__
    except AttributeError:
        path = module
    directory = os.path.dirname(path)
    if parent:
        directory = os.path.join(directory, os.pardir)
    absolute = os.path.abspath(directory)
    normalized = os.path.normpath(absolute)
    return normalized


def git_clean(remove_directories=False, force=False, dry_run=False, interactive=False, quiet=False, exclude=None,
              ignore_rules=False, clean_ignored=False, paths=None):
    """Execute git clean commands."""
    command = ['git', 'clean']
    if remove_directories:
        command.append('-d')
    if force:
        command.append('--force')
    if interactive:
        command.append('--interactive')
    if quiet:
        command.append('--quiet')
    if dry_run:
        command.append('--dry-run')
    if exclude:
        try:
            exclude = exclude.split(' ')
        except AttributeError:
            pass
        for exclusion in exclude:
            command.append('--exclude={pattern}'.format(pattern=exclusion))
    if ignore_rules:
        command.append('-x')
    if clean_ignored:
        command.append('-X')
    if paths:
        try:
            paths = paths.split(' ')
        except AttributeError:
            pass
        command.extend(paths)
    return subprocess.check_output(command)


def clean_bytecode():
    """Clean bytecode files."""
    try:
        result = git_clean(
            remove_directories=True,
            force=True,
            exclude=[
                '*.*',  # exclude everything
                '!*.py[co]',  # except bytecode
                '!**/__pycache__/',  # and __pycache__ folders
            ],
        )
        print(result)
    except subprocess.CalledProcessError as error:
        sys.exit('Error Code: {}'.format(error.returncode))
    except (IOError, OSError) as error:
        sys.exit('Error: {}'.format(error))
    else:
        return result


def clean_folders(*paths):
    """Clean obsolete folders."""
    try:
        result = git_clean(
            remove_directories=True,
            force=True,
            ignore_rules=True,
            paths=paths,
        )
    except subprocess.CalledProcessError as error:
        sys.exit('Error Code: {}'.format(error.returncode))
    except (IOError, OSError) as error:
        sys.exit('Error: {}'.format(error))
    else:
        return result


def force_clean_folder(path, required):
    """
    Force clean a folder and exclude any required subfolders.

    :param path: Target folder to remove subfolders
    :param required: Keep only the required subfolders
    """
    root, dirs, files = next(os.walk(path))
    required = sorted(required)
    if required:
        print('Skipping required subfolders', required)
    remove = sorted(set(dirs).difference(required))
    missing = sorted(set(required).difference(dirs))
    for path in remove:
        pathname = os.path.join(root, path)
        print('Removing', pathname)
        shutil.rmtree(pathname)
    if missing:
        raise Exception('Required subfolders missing:', missing)


def clean(paths):
    """Clean up bytecode and obsolete folders."""
    def _report_error(msg):
        print('WARNING: Automatic cleanup could not be executed.')
        print('         If errors occur, manual cleanup may be required.')
        print('REASON : {}'.format(msg))

    with WorkingDirectory(module_path()) as cwd:
        if cwd.working_directory != cwd.original_directory:
            print('Changing to directory:', cwd.working_directory)

        print('\n-- Cleaning bytecode --')
        try:
            result = clean_bytecode()
        except SystemExit as error:
            _report_error(error)
        else:
            print(result or 'No bytecode to clean')

        if paths and os.path.exists('.git'):
            print('\n-- Cleaning folders: {} --'.format(list(paths)))
            try:
                result = clean_folders(*paths)
            except SystemExit as error:
                _report_error(error)
            else:
                print(result or 'No folders to clean\n')
        else:
            print('\nDirectory is not a git repository')
            try:
                items = paths.items()
            except AttributeError:
                _report_error('Failed to clean, no subfolder structure given')
            else:
                for folder, subfolders in items:
                    print('\nForce cleaning folder:', folder)
                    force_clean_folder(folder, subfolders)

        if cwd.working_directory != cwd.original_directory:
            print('Returning to directory: ', cwd.original_directory)

        print('\n-- Cleanup finished --\n')


if __name__ == '__main__':
    clean(FOLDER_STRUCTURE)
