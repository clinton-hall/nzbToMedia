
import os
import sys

import libs.util

ROOT_DIR = libs.util.module_root()
LIB_DIR = os.path.join(ROOT_DIR, 'libs')

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
    lib: os.path.join(LIB_DIR, lib)
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
            LOADED[name] = path
            return path


def add_all_libs():
    for lib in MANDATORY:
        add_libs(lib)
    return is_finished()


def is_finished():
    return MANDATORY.issubset(LOADED.keys())
