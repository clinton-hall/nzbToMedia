
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
import site
import sys

import libs.util

LIB_ROOT = libs.util.module_path()

COMMON = 'common'
CUSTOM = 'custom'
PY2 = 'py2'
WIN = 'win'

LOADED = {}
MANDATORY = {
    COMMON,
    CUSTOM,
}
DIRECTORY = {
    lib: os.path.join(LIB_ROOT, lib)
    for lib in [COMMON, CUSTOM, PY2, WIN]
}

if sys.platform == 'win32':
    MANDATORY.add(WIN)

if sys.version_info < (3, ):
    MANDATORY.add(PY2)


def add_libs(name):
    if name in MANDATORY and name not in LOADED:
        path = libs.util.add_path(DIRECTORY[name])
        if path:
            site.addsitedir(path)
            LOADED[name] = path
            return path


def add_all_libs():
    for lib in [COMMON, CUSTOM, PY2, WIN]:
        if lib not in MANDATORY:
            continue
        add_libs(lib)
    return is_finished()


def is_finished():
    return MANDATORY.issubset(LOADED.keys())
