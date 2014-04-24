import os
import logging

Logger = logging.getLogger()

def process_all_exceptions(name, dirname):
    for group, exception in __customgroups__.items():
        if not (group in name or group in dirname):
            continue
        process_exception(exception, name, dirname)

def process_exception(exception, name, dirname):
    for filename in listMediaFiles(dirname):
        parentDir = os.path.dirname(filename)
        exception(filename, parentDir)

def process_qoq(filename, dirname):
    logging.debug("Reversing the file name for a QoQ release %s", filename)
    head, fileExtension = os.path.splitext(os.path.basename(filename))
    newname = head[::-1]
    newfile = newname + fileExtension
    newfilePath = os.path.join(dirname, newfile)
    os.rename(filename, newfilePath)
    logging.debug("New file name is %s", newfile)

# dict for custom groups
# we can add more to this list
__customgroups__ = {'Q o Q': process_qoq}
