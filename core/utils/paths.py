
from functools import partial
import os
import re

from six import text_type

import core


def make_dir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except Exception:
            return False
    return True


def remote_dir(path):
    if not core.REMOTEPATHS:
        return path
    for local, remote in core.REMOTEPATHS:
        if local in path:
            base_dirs = path.replace(local, '').split(os.sep)
            if '/' in remote:
                remote_sep = '/'
            else:
                remote_sep = '\\'
            new_path = remote_sep.join([remote] + base_dirs)
            new_path = re.sub(r'(\S)(\\+)', r'\1\\', new_path)
            new_path = re.sub(r'(/+)', r'/', new_path)
            new_path = re.sub(r'([/\\])$', r'', new_path)
            return new_path
    return path


def get_dir_size(input_path):
    prepend = partial(os.path.join, input_path)
    return sum([
        (os.path.getsize(f) if os.path.isfile(f) else get_dir_size(f))
        for f in map(prepend, os.listdir(text_type(input_path)))
    ])
