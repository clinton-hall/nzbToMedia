
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

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
