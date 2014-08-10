import os
import re
from nzbtomedia import logger
from nzbtomedia.nzbToMediaUtil import listMediaFiles

reverse_list = [r"\.\d{2}e\d{2}s\.", r"\.[pi]0801\.", r"\.p027\.", r"\.[pi]675\.", r"\.[pi]084\.", r"\.p063\.", r"\b[45]62[xh]\.", r"\.yarulb\.", r"\.vtd[hp]\.", 
                r"\.ld[.-]?bew\.", r"\.pir.?(dov|dvd|bew|db|rb)\.", r"\brdvd\.", r"\.vts\.", r"\.reneercs\.", r"\.dcv\.", r"\b(pir|mac)dh\b", r"\.reporp\.", r"\.kcaper\.", 
                r"\.lanretni\.", r"\b3ca\b", r"\.cstn\."]
reverse_pattern = re.compile('|'.join(reverse_list), flags=re.IGNORECASE)
season_pattern = re.compile(r"(.*\.\d{2}e\d{2}s\.)(.*)", flags=re.IGNORECASE)
word_pattern = re.compile(r"([^A-Z0-9]*[A-Z0-9]+)")
media_list = [r"\.s\d{2}e\d{2}\.", r"\.1080[pi]\.", r"\.720p\.", r"\.576[pi]", r"\.480[pi]\.", r"\.360p\.", r"\.[xh]26[45]\b", r"\.bluray\.", r"\.[hp]dtv\.", 
              r"\.web[.-]?dl\.", r"\.(vod|dvd|web|bd|br).?rip\.", r"\.dvdr\b", r"\.stv\.", r"\.screener\.", r"\.vcd\.", r"\bhd(cam|rip)\b", r"\.proper\.", r"\.repack\.", 
              r"\.internal\.", r"\bac3\b", r"\.ntsc\.", r"\.pal\.", r"\.secam\.", r"\bdivx\b", r"\bxvid\b"]
media_pattern = re.compile('|'.join(media_list), flags=re.IGNORECASE)
garbage_name = re.compile(r"^[a-zA-Z0-9]*$")
char_replace = [[r"(\w)1\.(\w)",r"\1i\2"]
]

def process_all_exceptions(name, dirname):
    rename_script(dirname)
    for filename in listMediaFiles(dirname):
        parentDir = os.path.dirname(filename)
        head, fileExtension = os.path.splitext(os.path.basename(filename))
        if reverse_pattern.search(head) is not None:
            exception = reverse_filename        
        elif garbage_name.search(head) is not None:
            exception = replace_filename
        else:
            continue
        exception(filename, parentDir, name)

def replace_filename(filename, dirname, name):
    head, fileExtension = os.path.splitext(os.path.basename(filename))
    if media_pattern.search(os.path.basename(dirname).replace(' ','.')) is not None: 
        newname = os.path.basename(dirname).replace(' ', '.')
        logger.debug("Replacing file name %s with directory name %s" % (head, newname), "EXCEPTION")
    elif media_pattern.search(name.replace(' ','.').lower()) is not None:
        newname = name.replace(' ', '.')
        logger.debug("Replacing file name %s with download name %s" % (head, newname), "EXCEPTION")
    else:
        logger.warning("No name replacement determined for %s" % (head), "EXCEPTION")
        return 
    newfile = newname + fileExtension
    newfilePath = os.path.join(dirname, newfile)
    try:
        os.rename(filename, newfilePath)
    except Exception,e:
        logger.error("Unable to rename file due to: %s" % (str(e)), "EXCEPTION")

def reverse_filename(filename, dirname, name):
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
    newname = newname.replace(' ', '.')
    logger.debug("Reversing filename %s to %s" % (head, newname), "EXCEPTION")
    newfile = newname + fileExtension
    newfilePath = os.path.join(dirname, newfile)
    try:
        os.rename(filename, newfilePath)
    except Exception,e:
        logger.error("Unable to rename file due to: %s" % (str(e)), "EXCEPTION")

def rename_script(dirname):
    rename_file = ""
    for dir, dirs, files in os.walk(dirname):
        for file in files:
            if re.search('(rename\S*\.(sh|bat))',file):
                rename_file = os.path.join(dir, file)
                dirname = dir
                break
    if rename_file: 
        rename_lines = [line.strip() for line in open(rename_file)]
        for line in rename_lines:
            cmd = filter(None, re.split('mv|Move\s(\S*)\s(\S*)',line))
            if len(cmd) == 2 and os.path.isfile(os.path.join(dirname, cmd[0])):
                orig = os.path.join(dirname, cmd[0])
                dest = os.path.join(dirname, cmd[1].split('\\')[-1].split('/')[-1])
                if os.path.isfile(dest):
                    continue
                logger.debug("Renaming file %s to %s" % (orig, dest), "EXCEPTION")
                try:
                    os.rename(orig, dest)
                except Exception,e:
                    logger.error("Unable to rename file due to: %s" % (str(e)), "EXCEPTION")

# dict for custom groups
# we can add more to this list
#__customgroups__ = {'Q o Q': process_qoq, '-ECI': process_eci}
                
