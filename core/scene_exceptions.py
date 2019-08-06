# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
import platform
import re
import shlex
import subprocess

import core
from core import logger
from core.utils import list_media_files

reverse_list = [r'\.\d{2}e\d{2}s\.', r'\.[pi]0801\.', r'\.p027\.', r'\.[pi]675\.', r'\.[pi]084\.', r'\.p063\.',
                r'\b[45]62[xh]\.', r'\.yarulb\.', r'\.vtd[hp]\.',
                r'\.ld[.-]?bew\.', r'\.pir.?(dov|dvd|bew|db|rb)\.', r'\brdvd\.', r'\.vts\.', r'\.reneercs\.',
                r'\.dcv\.', r'\b(pir|mac)dh\b', r'\.reporp\.', r'\.kcaper\.',
                r'\.lanretni\.', r'\b3ca\b', r'\.cstn\.']
reverse_pattern = re.compile('|'.join(reverse_list), flags=re.IGNORECASE)
season_pattern = re.compile(r'(.*\.\d{2}e\d{2}s\.)(.*)', flags=re.IGNORECASE)
word_pattern = re.compile(r'([^A-Z0-9]*[A-Z0-9]+)')
media_list = [r'\.s\d{2}e\d{2}\.', r'\.1080[pi]\.', r'\.720p\.', r'\.576[pi]', r'\.480[pi]\.', r'\.360p\.',
              r'\.[xh]26[45]\b', r'\.bluray\.', r'\.[hp]dtv\.',
              r'\.web[.-]?dl\.', r'\.(vod|dvd|web|bd|br).?rip\.', r'\.dvdr\b', r'\.stv\.', r'\.screener\.', r'\.vcd\.',
              r'\bhd(cam|rip)\b', r'\.proper\.', r'\.repack\.',
              r'\.internal\.', r'\bac3\b', r'\.ntsc\.', r'\.pal\.', r'\.secam\.', r'\bdivx\b', r'\bxvid\b']
media_pattern = re.compile('|'.join(media_list), flags=re.IGNORECASE)
garbage_name = re.compile(r'^[a-zA-Z0-9]*$')
char_replace = [[r'(\w)1\.(\w)', r'\1i\2'],
                ]


def process_all_exceptions(name, dirname):
    par2(dirname)
    rename_script(dirname)
    for filename in list_media_files(dirname):
        newfilename = None
        parent_dir = os.path.dirname(filename)
        head, file_extension = os.path.splitext(os.path.basename(filename))
        if reverse_pattern.search(head) is not None:
            exception = reverse_filename
        elif garbage_name.search(head) is not None:
            exception = replace_filename
        else:
            exception = None
            newfilename = filename
        if not newfilename:
            newfilename = exception(filename, parent_dir, name)
        if core.GROUPS:
            newfilename = strip_groups(newfilename)
        if newfilename != filename:
            rename_file(filename, newfilename)


def strip_groups(filename):
    if not core.GROUPS:
        return filename
    dirname, file = os.path.split(filename)
    head, file_extension = os.path.splitext(file)
    newname = head.replace(' ', '.')
    for group in core.GROUPS:
        newname = newname.replace(group, '')
        newname = newname.replace('[]', '')
    newfile = newname + file_extension
    newfile_path = os.path.join(dirname, newfile)
    return newfile_path


def rename_file(filename, newfile_path):
    if os.path.isfile(newfile_path):
        newfile_path = os.path.splitext(newfile_path)[0] + '.NTM' + os.path.splitext(newfile_path)[1]
    logger.debug('Replacing file name {old} with download name {new}'.format
                 (old=filename, new=newfile_path), 'EXCEPTION')
    try:
        os.rename(filename, newfile_path)
    except Exception as error:
        logger.error('Unable to rename file due to: {error}'.format(error=error), 'EXCEPTION')


def replace_filename(filename, dirname, name):
    head, file_extension = os.path.splitext(os.path.basename(filename))
    if media_pattern.search(os.path.basename(dirname).replace(' ', '.')) is not None:
        newname = os.path.basename(dirname).replace(' ', '.')
        logger.debug('Replacing file name {old} with directory name {new}'.format(old=head, new=newname), 'EXCEPTION')
    elif media_pattern.search(name.replace(' ', '.').lower()) is not None:
        newname = name.replace(' ', '.')
        logger.debug('Replacing file name {old} with download name {new}'.format
                     (old=head, new=newname), 'EXCEPTION')
    else:
        logger.warning('No name replacement determined for {name}'.format(name=head), 'EXCEPTION')
        newname = name
    newfile = newname + file_extension
    newfile_path = os.path.join(dirname, newfile)
    return newfile_path


def reverse_filename(filename, dirname, name):
    head, file_extension = os.path.splitext(os.path.basename(filename))
    na_parts = season_pattern.search(head)
    if na_parts is not None:
        word_p = word_pattern.findall(na_parts.group(2))
        if word_p:
            new_words = ''
            for wp in word_p:
                if wp[0] == '.':
                    new_words += '.'
                new_words += re.sub(r'\W', '', wp)
        else:
            new_words = na_parts.group(2)
        for cr in char_replace:
            new_words = re.sub(cr[0], cr[1], new_words)
        newname = new_words[::-1] + na_parts.group(1)[::-1]
    else:
        newname = head[::-1].title()
    newname = newname.replace(' ', '.')
    logger.debug('Reversing filename {old} to {new}'.format
                 (old=head, new=newname), 'EXCEPTION')
    newfile = newname + file_extension
    newfile_path = os.path.join(dirname, newfile)
    return newfile_path


def rename_script(dirname):
    rename_file = ''
    for directory, _, files in os.walk(dirname):
        for file in files:
            if re.search(r'(rename\S*\.(sh|bat)$)', file, re.IGNORECASE):
                rename_file = os.path.join(directory, file)
                dirname = directory
                break
    if rename_file:
        rename_lines = [line.strip() for line in open(rename_file)]
        for line in rename_lines:
            if re.search('^(mv|Move)', line, re.IGNORECASE):
                cmd = shlex.split(line)[1:]
            else:
                continue
            if len(cmd) == 2 and os.path.isfile(os.path.join(dirname, cmd[0])):
                orig = os.path.join(dirname, cmd[0])
                dest = os.path.join(dirname, cmd[1].split('\\')[-1].split('/')[-1])
                if os.path.isfile(dest):
                    continue
                logger.debug('Renaming file {source} to {destination}'.format
                             (source=orig, destination=dest), 'EXCEPTION')
                try:
                    os.rename(orig, dest)
                except Exception as error:
                    logger.error('Unable to rename file due to: {error}'.format(error=error), 'EXCEPTION')


def par2(dirname):
    sofar = 0
    parfile = ''
    objects = []
    if os.path.exists(dirname):
        objects = os.listdir(dirname)
    for item in objects:
        if item.endswith('.par2'):
            size = os.path.getsize(os.path.join(dirname, item))
            if size > sofar:
                sofar = size
                parfile = item
    if core.PAR2CMD and parfile:
        pwd = os.getcwd()  # Get our Present Working Directory
        os.chdir(dirname)  # set directory to run par on.
        if platform.system() == 'Windows':
            bitbucket = open('NUL')
        else:
            bitbucket = open('/dev/null')
        logger.info('Running par2 on file {0}.'.format(parfile), 'PAR2')
        command = [core.PAR2CMD, 'r', parfile, '*']
        cmd = ''
        for item in command:
            cmd = '{cmd} {item}'.format(cmd=cmd, item=item)
        logger.debug('calling command:{0}'.format(cmd), 'PAR2')
        try:
            proc = subprocess.Popen(command, stdout=bitbucket, stderr=bitbucket)
            proc.communicate()
            result = proc.returncode
        except Exception:
            logger.error('par2 file processing for {0} has failed'.format(parfile), 'PAR2')
        if result == 0:
            logger.info('par2 file processing succeeded', 'PAR2')
        os.chdir(pwd)
        bitbucket.close()

# dict for custom groups
# we can add more to this list
# _customgroups = {'Q o Q': process_qoq, '-ECI': process_eci}
