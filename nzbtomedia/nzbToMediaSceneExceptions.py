import os
import re
import logging

Logger = logging.getLogger()
reverse_list = [r"\.\d{2}e\d{2}s\.", r"\.[pi]0801\.", r"\.p027\.", r"\b[45]62[xh]\.", r"\.yarulb\.", r"\.vtdh\.", r"\.ld[.-]?bew\.", r"\.pir[dvd|bew|db|rb]\."]
reverse_pattern = re.compile('|'.join(reverse_list), flags=re.IGNORECASE)
season_pattern = re.compile(r"(.*\.\d{2}e\d{2}s\.)(.*)", flags=re.IGNORECASE)
word_pattern = re.compile(r"([^A-Z0-9]*[A-Z0-9]+)")
char_replace = [[r"(\w)1\.(\w)",r"\1i\2"]
]

def process_all_exceptions(name, dirname):
    for filename in listMediaFiles(dirname):
        if reverse_pattern.search(filename) is not None:
            exception = process_reverse
            parentDir = os.path.dirname(filename)
            exception(filename, parentDir)
        else:           
            for group, exception in __customgroups__.items():
                if not (group in name or group in dirname or group in filename):
                    continue
                parentDir = os.path.dirname(filename)
                exception(filename, parentDir)

def process_qoq(filename, dirname):
    logging.debug("Reversing the file name for a QoQ release %s" % (filename), EXCEPTION)
    head, fileExtension = os.path.splitext(os.path.basename(filename))
    newname = head[::-1]
    newfile = newname + fileExtension
    newfilePath = os.path.join(dirname, newfile)
    os.rename(filename, newfilePath)
    logging.debug("New file name is %s" % (newfile), EXCEPTION)

def process_eci(filename, dirname):
    logging.debug("Replacing file name %s with directory name %s an -ECI release" % (filename, os.path.basename(dirname)), EXCEPTION)
    head, fileExtension = os.path.splitext(os.path.basename(filename))
    newname = os.path.basename(dirname)
    newfile = newname + fileExtension
    newfilePath = os.path.join(dirname, newfile)
    os.rename(filename, newfilePath)
    logging.debug("New file name is %s" % (newfile), EXCEPTION)

def process_reverse(filename, dirname):
    head, fileExtension = os.path.splitext(os.path.basename(filename))
    na_parts = season_pattern.search(head)
    if na_parts is not None:
        word_p = word_pattern.findall(na_parts.group(2))
        if word_P:
            new_words = ""
            for wp in word_p:
                if wp[0] == ".":
                    new_words += "."
                new_words += re.sub(r"\W","",wp)
        else:
            new_words = na_parts.group(2)
        for cr in char_replace:
            new_words = re.sub(cr[0],cr[1],new_words)
        newname = new_words[::-1] + na_parts.group(1)[::-1]
    else:
        newname = head[::-1].title()
    logging.debug("Reversing filename %s to %s" % (head, newname), EXCEPTION)
    newfile = newname + fileExtension
    newfilePath = os.path.join(dirname, newfile)
    try:
        os.rename(filename, newfilePath)
    except Exception,e:
        logging.error("Unable to rename file due to: %s" % (str(e)), EXCEPTION)

# dict for custom groups
# we can add more to this list
__customgroups__ = {'Q o Q': process_qoq, '-ECI': process_eci}
                
