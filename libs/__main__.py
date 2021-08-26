
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import shutil
import os
import time
import libs

if __name__ == '__main__':
    os.chdir(libs.LIB_ROOT)
    for lib, directory in libs.DIRECTORY.items():
        if lib == 'custom':
            continue
        try:
            shutil.rmtree(directory)
        except FileNotFoundError:
            pass
        else:
            print('Removed', directory)
        time.sleep(10)
        requirements = 'requirements-{name}.txt'.format(name=lib)
        libs.util.install_requirements(requirements, file=True, path=directory)
