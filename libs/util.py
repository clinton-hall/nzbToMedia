
import subprocess
import sys
import os

__all__ = [
    'module_path',
    'add_path',
]


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


def add_path(path, index=0):
    sys.path.insert(index, path)
    try:
        sys.path.index(path)
    except ValueError:
        return
    else:
        return path


def install_requirements(
        requirements,
        upgrade=True,
        path=None,
        file=False,
        executable=sys.executable,
):

    args = [
        executable,
        '-m',
        'pip',
        'install',
    ]

    if file:
        args.append('-r')
    args.append(requirements)

    if upgrade:
        args.append('--upgrade')

    if path is not None:
        args.append('--target')
        args.append(path)

    subprocess.call(args)


def git_clean(remove_directories=False, force=False, dry_run=False, interactive=False, quiet=False, exclude=None,
              ignore_rules=False, clean_ignored=False, paths=None):
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
        command.append('--exclude={pattern}'.format(pattern=exclude))
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
