# System imports
import os
import logging

# Custom imports
from nzbToMediaUtil import iterate_media_files


Logger = logging.getLogger()


def process_all_exceptions(name, dirname):
    for group, exception in __customgroups__.items():
        if not group in name:
            continue
        process_exception(exception, name, dirname)


def process_exception(exception, name, dirname):
    for parentDir, filename in iterate_media_files(dirname):
        exception(filename, parentDir)


def process_qoq(filename, dirname):
    Logger.debug("Reversing the file name for a QoQ release %s", filename)
    head, fileExtention = os.path.splitext(filename)
    newname = head[::-1]
    newfile = newname + fileExtention
    newfilePath = os.path.join(dirname, newfile)
    os.rename(filename, newfilePath)
    Logger.debug("New file name is %s", newfile)

# dict for custom groups
# we can add more to this list
__customgroups__ = {'[=-< Q o Q >-=]': process_qoq}
