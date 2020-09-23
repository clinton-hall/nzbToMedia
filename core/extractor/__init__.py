# coding=utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
import platform
import shutil
import stat
import subprocess
from subprocess import Popen, call
from time import sleep

import core


def extract(file_path, output_destination):
    success = 0
    # Using Windows
    if platform.system() == 'Windows':
        if not os.path.exists(core.SEVENZIP):
            core.logger.error('EXTRACTOR: Could not find 7-zip, Exiting')
            return False
        wscriptlocation = os.path.join(os.environ['WINDIR'], 'system32', 'wscript.exe')
        invislocation = os.path.join(core.APP_ROOT, 'core', 'extractor', 'bin', 'invisible.vbs')
        cmd_7zip = [wscriptlocation, invislocation, str(core.SHOWEXTRACT), core.SEVENZIP, 'x', '-y']
        ext_7zip = ['.rar', '.zip', '.tar.gz', 'tgz', '.tar.bz2', '.tbz', '.tar.lzma', '.tlz', '.7z', '.xz', '.gz']
        extract_commands = dict.fromkeys(ext_7zip, cmd_7zip)
    # Using unix
    else:
        required_cmds = ['unrar', 'unzip', 'tar', 'unxz', 'unlzma', '7zr', 'bunzip2', 'gunzip']
        # ## Possible future suport:
        # gunzip: gz (cmd will delete original archive)
        # ## the following do not extract to dest dir
        # '.xz': ['xz', '-d --keep'],
        # '.lzma': ['xz', '-d --format=lzma --keep'],
        # '.bz2': ['bzip2', '-d --keep'],

        extract_commands = {
            '.rar': ['unrar', 'x', '-o+', '-y'],
            '.tar': ['tar', '-xf'],
            '.zip': ['unzip'],
            '.tar.gz': ['tar', '-xzf'], '.tgz': ['tar', '-xzf'],
            '.tar.bz2': ['tar', '-xjf'], '.tbz': ['tar', '-xjf'],
            '.tar.lzma': ['tar', '--lzma', '-xf'], '.tlz': ['tar', '--lzma', '-xf'],
            '.tar.xz': ['tar', '--xz', '-xf'], '.txz': ['tar', '--xz', '-xf'],
            '.7z': ['7zr', 'x'],
            '.gz': ['gunzip'],
        }
        # Test command exists and if not, remove
        if not os.getenv('TR_TORRENT_DIR'):
            devnull = open(os.devnull, 'w')
            for cmd in required_cmds:
                if call(['which', cmd], stdout=devnull,
                        stderr=devnull):  # note, returns 0 if exists, or 1 if doesn't exist.
                    for k, v in extract_commands.items():
                        if cmd in v[0]:
                            if not call(['which', '7zr'], stdout=devnull, stderr=devnull):  # we do have '7zr'
                                extract_commands[k] = ['7zr', 'x', '-y']
                            elif not call(['which', '7z'], stdout=devnull, stderr=devnull):  # we do have '7z'
                                extract_commands[k] = ['7z', 'x', '-y']
                            elif not call(['which', '7za'], stdout=devnull, stderr=devnull):  # we do have '7za'
                                extract_commands[k] = ['7za', 'x', '-y']
                            else:
                                core.logger.error('EXTRACTOR: {cmd} not found, '
                                                  'disabling support for {feature}'.format
                                                  (cmd=cmd, feature=k))
                                del extract_commands[k]
            devnull.close()
        else:
            core.logger.warning('EXTRACTOR: Cannot determine which tool to use when called from Transmission')

        if not extract_commands:
            core.logger.warning('EXTRACTOR: No archive extracting programs found, plugin will be disabled')

    ext = os.path.splitext(file_path)
    cmd = []
    if ext[1] in ('.gz', '.bz2', '.lzma'):
        # Check if this is a tar
        if os.path.splitext(ext[0])[1] == '.tar':
            cmd = extract_commands['.tar{ext}'.format(ext=ext[1])]
        else: # Try gunzip
            cmd = extract_commands[ext[1]]
    elif ext[1] in ('.1', '.01', '.001') and os.path.splitext(ext[0])[1] in ('.rar', '.zip', '.7z'):
        cmd = extract_commands[os.path.splitext(ext[0])[1]]
    elif ext[1] in ('.cb7', '.cba', '.cbr', '.cbt', '.cbz'):  # don't extract these comic book archives.
        return False
    else:
        if ext[1] in extract_commands:
            cmd = extract_commands[ext[1]]
        else:
            core.logger.debug('EXTRACTOR: Unknown file type: {ext}'.format
                              (ext=ext[1]))
            return False

        # Create outputDestination folder
        core.make_dir(output_destination)

    if core.PASSWORDS_FILE and os.path.isfile(os.path.normpath(core.PASSWORDS_FILE)):
        passwords = [line.strip() for line in open(os.path.normpath(core.PASSWORDS_FILE))]
    else:
        passwords = []

    core.logger.info('Extracting {file} to {destination}'.format
                     (file=file_path, destination=output_destination))
    core.logger.debug('Extracting {cmd} {file} {destination}'.format
                      (cmd=cmd, file=file_path, destination=output_destination))

    orig_files = []
    orig_dirs = []
    for directory, subdirs, files in os.walk(output_destination):
        for subdir in subdirs:
            orig_dirs.append(os.path.join(directory, subdir))
        for file in files:
            orig_files.append(os.path.join(directory, file))

    pwd = os.getcwd()  # Get our Present Working Directory
    os.chdir(output_destination)  # Not all unpack commands accept full paths, so just extract into this directory
    devnull = open(os.devnull, 'w')

    try:  # now works same for nt and *nix
        info = None
        cmd.append(file_path)  # add filePath to final cmd arg.
        if platform.system() == 'Windows':
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            cmd = core.NICENESS + cmd
        cmd2 = cmd
        if not 'gunzip' in cmd: #gunzip doesn't support password
            cmd2.append('-p-')  # don't prompt for password.
        p = Popen(cmd2, stdout=devnull, stderr=devnull, startupinfo=info)  # should extract files fine.
        res = p.wait()
        if res == 0:  # Both Linux and Windows return 0 for successful.
            core.logger.info('EXTRACTOR: Extraction was successful for {file} to {destination}'.format
                             (file=file_path, destination=output_destination))
            success = 1
        elif len(passwords) > 0 and not 'gunzip' in cmd:
            core.logger.info('EXTRACTOR: Attempting to extract with passwords')
            for password in passwords:
                if password == '':  # if edited in windows or otherwise if blank lines.
                    continue
                cmd2 = cmd
                # append password here.
                passcmd = '-p{pwd}'.format(pwd=password)
                cmd2.append(passcmd)
                p = Popen(cmd2, stdout=devnull, stderr=devnull, startupinfo=info)  # should extract files fine.
                res = p.wait()
                if (res >= 0 and platform == 'Windows') or res == 0:
                    core.logger.info('EXTRACTOR: Extraction was successful '
                                     'for {file} to {destination} using password: {pwd}'.format
                                     (file=file_path, destination=output_destination, pwd=password))
                    success = 1
                    break
                else:
                    continue
    except Exception:
        core.logger.error('EXTRACTOR: Extraction failed for {file}. '
                          'Could not call command {cmd}'.format
                          (file=file_path, cmd=cmd))
        os.chdir(pwd)
        return False

    devnull.close()
    os.chdir(pwd)  # Go back to our Original Working Directory
    if success:
        # sleep to let files finish writing to disk
        sleep(3)
        perms = stat.S_IMODE(os.lstat(os.path.split(file_path)[0]).st_mode)
        for directory, subdirs, files in os.walk(output_destination):
            for subdir in subdirs:
                if not os.path.join(directory, subdir) in orig_files:
                    try:
                        os.chmod(os.path.join(directory, subdir), perms)
                    except Exception:
                        pass
            for file in files:
                if not os.path.join(directory, file) in orig_files:
                    try:
                        shutil.copymode(file_path, os.path.join(directory, file))
                    except Exception:
                        pass
        return True
    else:
        core.logger.error('EXTRACTOR: Extraction failed for {file}. '
                          'Result was {result}'.format
                          (file=file_path, result=res))
        return False
