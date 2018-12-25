from __future__ import print_function

import subprocess
import sys


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
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
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
        sys.exit(error.returncode)
    else:
        return result


def clean(*paths):
    """Clean up bytecode and obsolete folders."""
    print('-- Cleaning bytecode --')
    result = clean_bytecode()
    print(result or 'No bytecode to clean\n')
    if paths:
        print('-- Cleaning folders: {} --'.format(paths))
        result = clean_folders(*paths)
        print(result or 'No folders to clean\n')


if __name__ == '__main__':
    clean('libs', 'core')
