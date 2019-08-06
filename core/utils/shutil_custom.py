from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from functools import partial
import shutil
from six import PY2


def monkey_patch(length=512 * 1024):
    if PY2:
        # On Python 2 monkey patch shutil.copyfileobj()
        # to adjust the buffer length to 512KB rather than 4KB
        original_copyfileobj = shutil.copyfileobj
        shutil.copyfileobj = partial(original_copyfileobj, length=length)
