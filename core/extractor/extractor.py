# coding=utf-8

import os
import platform
import shutil
import stat
from time import sleep
import core
from subprocess import call, Popen
import subprocess


def extract(filePath, outputDestination):
    success = 0
    # Using Windows
    if platform.system() == 'Windows':
        if not os.path.exists(core.SEVENZIP):
            core.logger.error("EXTRACTOR: Could not find 7-zip, Exiting")
            return False
        invislocation = os.path.join(core.PROGRAM_DIR, 'core', 'extractor', 'bin', 'invisible.cmd')
        cmd_7zip = [invislocation, core.SEVENZIP, "x", "-y"]
        ext_7zip = [".rar", ".zip", ".tar.gz", "tgz", ".tar.bz2", ".tbz", ".tar.lzma", ".tlz", ".7z", ".xz"]
        EXTRACT_COMMANDS = dict.fromkeys(ext_7zip, cmd_7zip)
    # Using unix
    else:
        required_cmds = ["unrar", "unzip", "tar", "unxz", "unlzma", "7zr", "bunzip2"]
        # ## Possible future suport:
        # gunzip: gz (cmd will delete original archive)
        # ## the following do not extract to dest dir
        # ".xz": ["xz", "-d --keep"],
        # ".lzma": ["xz", "-d --format=lzma --keep"],
        # ".bz2": ["bzip2", "-d --keep"],

        EXTRACT_COMMANDS = {
            ".rar": ["unrar", "x", "-o+", "-y"],
            ".tar": ["tar", "-xf"],
            ".zip": ["unzip"],
            ".tar.gz": ["tar", "-xzf"], ".tgz": ["tar", "-xzf"],
            ".tar.bz2": ["tar", "-xjf"], ".tbz": ["tar", "-xjf"],
            ".tar.lzma": ["tar", "--lzma", "-xf"], ".tlz": ["tar", "--lzma", "-xf"],
            ".tar.xz": ["tar", "--xz", "-xf"], ".txz": ["tar", "--xz", "-xf"],
            ".7z": ["7zr", "x"],
        }
        # Test command exists and if not, remove
        if not os.getenv('TR_TORRENT_DIR'):
            devnull = open(os.devnull, 'w')
            for cmd in required_cmds:
                if call(['which', cmd], stdout=devnull,
                        stderr=devnull):  # note, returns 0 if exists, or 1 if doesn't exist.
                    for k, v in EXTRACT_COMMANDS.items():
                        if cmd in v[0]:
                            if not call(["which", "7zr"], stdout=devnull, stderr=devnull):  # we do have "7zr"
                                EXTRACT_COMMANDS[k] = ["7zr", "x", "-y"]
                            elif not call(["which", "7z"], stdout=devnull, stderr=devnull):  # we do have "7z"
                                EXTRACT_COMMANDS[k] = ["7z", "x", "-y"]
                            elif not call(["which", "7za"], stdout=devnull, stderr=devnull):  # we do have "7za"
                                EXTRACT_COMMANDS[k] = ["7za", "x", "-y"]
                            else:
                                core.logger.error("EXTRACTOR: {cmd} not found, "
                                                  "disabling support for {feature}".format
                                                  (cmd=cmd, feature=k))
                                del EXTRACT_COMMANDS[k]
            devnull.close()
        else:
            core.logger.warning("EXTRACTOR: Cannot determine which tool to use when called from Transmission")

        if not EXTRACT_COMMANDS:
            core.logger.warning("EXTRACTOR: No archive extracting programs found, plugin will be disabled")

    ext = os.path.splitext(filePath)
    cmd = []
    if ext[1] in (".gz", ".bz2", ".lzma"):
        # Check if this is a tar
        if os.path.splitext(ext[0])[1] == ".tar":
            cmd = EXTRACT_COMMANDS[".tar{ext}".format(ext=ext[1])]
    elif ext[1] in (".1", ".01", ".001") and os.path.splitext(ext[0])[1] in (".rar", ".zip", ".7z"):
        cmd = EXTRACT_COMMANDS[os.path.splitext(ext[0])[1]]
    elif ext[1] in (".cb7", ".cba", ".cbr", ".cbt", ".cbz"):  # don't extract these comic book archives.
        return False
    else:
        if ext[1] in EXTRACT_COMMANDS:
            cmd = EXTRACT_COMMANDS[ext[1]]
        else:
            core.logger.debug("EXTRACTOR: Unknown file type: {ext}".format
                              (ext=ext[1]))
            return False

        # Create outputDestination folder
        core.makeDir(outputDestination)

    if core.PASSWORDSFILE != "" and os.path.isfile(os.path.normpath(core.PASSWORDSFILE)):
        passwords = [line.strip() for line in open(os.path.normpath(core.PASSWORDSFILE))]
    else:
        passwords = []

    core.logger.info("Extracting {file} to {destination}".format
                     (file=filePath, destination=outputDestination))
    core.logger.debug("Extracting {cmd} {file} {destination}".format
                      (cmd=cmd, file=filePath, destination=outputDestination))

    origFiles = []
    origDirs = []
    for dir, subdirs, files in os.walk(outputDestination):
        for subdir in subdirs:
            origDirs.append(os.path.join(dir, subdir))
        for file in files:
            origFiles.append(os.path.join(dir, file))

    pwd = os.getcwd()  # Get our Present Working Directory
    os.chdir(outputDestination)  # Not all unpack commands accept full paths, so just extract into this directory
    devnull = open(os.devnull, 'w')

    try:  # now works same for nt and *nix
        info = None
        cmd.append(filePath)  # add filePath to final cmd arg.
        if platform.system() == 'Windows':
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            cmd = core.NICENESS + cmd
        cmd2 = cmd
        cmd2.append("-p-")  # don't prompt for password.
        p = Popen(cmd2, stdout=devnull, stderr=devnull, startupinfo=info)  # should extract files fine.
        res = p.wait()
        if (res >= 0 and os.name == 'nt') or res == 0:  # for windows chp returns process id if successful or -1*Error code. Linux returns 0 for successful.
            core.logger.info("EXTRACTOR: Extraction was successful for {file} to {destination}".format
                             (file=filePath, destination=outputDestination))
            success = 1
        elif len(passwords) > 0:
            core.logger.info("EXTRACTOR: Attempting to extract with passwords")
            for password in passwords:
                if password == "":  # if edited in windows or otherwise if blank lines.
                    continue
                cmd2 = cmd
                # append password here.
                passcmd = "-p{pwd}".format(pwd=password)
                cmd2.append(passcmd)
                p = Popen(cmd2, stdout=devnull, stderr=devnull, startupinfo=info)  # should extract files fine.
                res = p.wait()
                if (res >= 0 and platform == 'Windows') or res == 0:
                    core.logger.info("EXTRACTOR: Extraction was successful "
                                     "for {file} to {destination} using password: {pwd}".format
                                     (file=filePath, destination=outputDestination, pwd=password))
                    success = 1
                    break
                else:
                    continue
    except:
        core.logger.error("EXTRACTOR: Extraction failed for {file}. "
                          "Could not call command {cmd}".format
                          (file=filePath, cmd=cmd))
        os.chdir(pwd)
        return False

    devnull.close()
    os.chdir(pwd)  # Go back to our Original Working Directory
    if success:
        # sleep to let files finish writing to disk
        sleep(3)
        perms = stat.S_IMODE(os.lstat(os.path.split(filePath)[0]).st_mode)
        for dir, subdirs, files in os.walk(outputDestination):
            for subdir in subdirs:
                if not os.path.join(dir, subdir) in origFiles:
                    try:
                        os.chmod(os.path.join(dir, subdir), perms)
                    except:
                        pass
            for file in files:
                if not os.path.join(dir, file) in origFiles:
                    try:
                        shutil.copymode(filePath, os.path.join(dir, file))
                    except:
                        pass
        return True
    else:
        core.logger.error("EXTRACTOR: Extraction failed for {file}. "
                          "Result was {result}".format
                          (file=filePath, result=res))
        return False
