from __future__ import print_function

import os
import subprocess
import sys


class WorkingDirectory(object):
    """Context manager for changing current working directory."""
    def __init__(self, new, original=None):
        self.working_directory = new
        self.original_directory = os.getcwd() if original is None else original

    def __enter__(self):
        os.chdir(self.working_directory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.original_directory)


def module_path(module=__file__, parent=False):
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


def clean(*paths):
    """Clean up bytecode and obsolete folders."""
    with WorkingDirectory(module_path()) as cwd:
        if cwd.working_directory != cwd.original_directory:
            print('Changing to directory:', cwd.working_directory)
        print('\n-- Cleaning bytecode --')
        try:
            result = clean_bytecode()
        except SystemExit as error:
            print(error)
        else:
            print(result or 'No bytecode to clean')
        if paths:
            print('\n-- Cleaning folders: {} --'.format(paths))
            try:
                result = clean_folders(*paths)
            except SystemExit as error:
                print(error)
            else:
                print(result or 'No folders to clean\n')
        if cwd.working_directory != cwd.original_directory:
            print('Returning to directory: ', cwd.original_directory)
        print('\n-- Cleanup finished --\n')


if __name__ == '__main__':
    clean('libs', 'core')
