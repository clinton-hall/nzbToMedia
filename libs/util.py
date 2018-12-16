
import subprocess
import sys
import os

__all__ = [
    'module_root',
    'add_path',
]


def module_root(module=__file__):
    try:
        path = module.__file__
    except AttributeError:
        path = module
    directory = os.path.dirname(path)
    parent = os.path.join(directory, os.pardir)
    absolute = os.path.abspath(parent)
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
