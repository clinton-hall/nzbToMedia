import os
import site
import sys

import libs.util

LIB_ROOT = libs.util.module_path()

COMMON = 'common'
WIN = 'win'

LOADED = {}
MANDATORY = {
    COMMON,
}
DIRECTORY = {
    lib: os.path.join(LIB_ROOT, lib)
    for lib in [COMMON, WIN]
}

if sys.platform == 'win32':
    MANDATORY.add(WIN)

if sys.version_info < (3, 6):
    raise RuntimeError('Python 3.6 or lower is no longer supported')


def add_libs(name):
    if name in MANDATORY and name not in LOADED:
        path = libs.util.add_path(DIRECTORY[name])
        if path:
            site.addsitedir(path)
            LOADED[name] = path
            return path


def add_all_libs():
    for lib in [COMMON, WIN]:
        if lib not in MANDATORY:
            continue
        add_libs(lib)
    return is_finished()


def is_finished():
    return MANDATORY.issubset(LOADED.keys())
