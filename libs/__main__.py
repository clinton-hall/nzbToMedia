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
        requirements = f'requirements-{lib}.txt'
        libs.util.install_requirements(requirements, file=True, path=directory)
