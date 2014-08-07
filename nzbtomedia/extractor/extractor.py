import os
import platform
from time import sleep
import nzbtomedia
from subprocess import call, Popen

def extract(filePath, outputDestination):
    success = 0
    # Using Windows
    if platform.system() == 'Windows':
        chplocation = nzbtomedia.os.path.join(nzbtomedia.PROGRAM_DIR, 'nzbtomedia/extractor/bin/chp.exe')
        sevenzipLocation = nzbtomedia.os.path.join(nzbtomedia.PROGRAM_DIR, 'nzbtomedia/extractor/bin/' + platform.machine() + '/7z.exe')

        if not os.path.exists(sevenzipLocation):
            nzbtomedia.logger.error("EXTRACTOR: Could not find 7-zip, Exiting")
            return False
        else:
            if not os.path.exists(chplocation):
                cmd_7zip = [sevenzipLocation, "x", "-y"]
            else:
                cmd_7zip = [chplocation, sevenzipLocation, "x", "-y"]
            ext_7zip = [".rar", ".zip", ".tar.gz", "tgz", ".tar.bz2", ".tbz", ".tar.lzma", ".tlz", ".7z", ".xz"]
            EXTRACT_COMMANDS = dict.fromkeys(ext_7zip, cmd_7zip)
    # Using unix
    else:
        required_cmds = ["unrar", "unzip", "tar", "unxz", "unlzma", "7zr", "bunzip2"]
        ## Possible future suport:
        # gunzip: gz (cmd will delete original archive)
        ## the following do not extract to dest dir
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
                if call(['which', cmd], stdout=devnull, stderr=devnull):  #note, returns 0 if exists, or 1 if doesn't exist.
                    if cmd == "7zr" and not call(["which", "7z"]):  # we do have "7z" command
                        EXTRACT_COMMANDS[".7z"] = ["7z", "x"]
                    else: 
                        for k, v in EXTRACT_COMMANDS.items():
                            if cmd in v[0]:
                                nzbtomedia.logger.error("EXTRACTOR: %s not found, disabling support for %s" % (cmd, k))
                                del EXTRACT_COMMANDS[k]
            devnull.close()
        else:
            nzbtomedia.logger.warning("EXTRACTOR: Cannot determine which tool to use when called from Transmission")

        if not EXTRACT_COMMANDS:
            nzbtomedia.logger.warning("EXTRACTOR: No archive extracting programs found, plugin will be disabled")

    ext = os.path.splitext(filePath)
    cmd = []
    if ext[1] in (".gz", ".bz2", ".lzma"):
        # Check if this is a tar
        if os.path.splitext(ext[0])[1] == ".tar":
            cmd = EXTRACT_COMMANDS[".tar" + ext[1]]
    elif ext[1] in (".1", ".01", ".001") and os.path.splitext(ext[0])[1] in (".rar", ".zip", ".7z"):
        cmd = EXTRACT_COMMANDS[os.path.splitext(ext[0])[1]]
    elif ext[1] in (".cb7", ".cba", ".cbr", ".cbt", ".cbz"):  # don't extract these comic book archives.
        return False
    else:
        if ext[1] in EXTRACT_COMMANDS:
            cmd = EXTRACT_COMMANDS[ext[1]]
        else:
            nzbtomedia.logger.debug("EXTRACTOR: Unknown file type: %s" % ext[1])
            return False

    # Create outputDestination folder
        nzbtomedia.makeDir(outputDestination)

    if nzbtomedia.PASSWORDSFILE != "" and os.path.isfile(os.path.normpath(nzbtomedia.PASSWORDSFILE)):
        passwords = [line.strip() for line in open(os.path.normpath(nzbtomedia.PASSWORDSFILE))]
    else:
        passwords = []
        nzbtomedia.logger.info("Extracting %s to %s" % (filePath, outputDestination))
        nzbtomedia.logger.debug("Extracting %s %s %s" % (cmd, filePath, outputDestination))

    pwd = os.getcwd()  # Get our Present Working Directory
    os.chdir(outputDestination)  # Not all unpack commands accept full paths, so just extract into this directory
    devnull = open(os.devnull, 'w')
    try:  # now works same for nt and *nix
        cmd.append(filePath)  # add filePath to final cmd arg.
        if platform.system() != 'Windows':
            cmd = nzbtomedia.NICENESS + cmd
        cmd2 = cmd
        cmd2.append("-p-")  # don't prompt for password.
        p = Popen(cmd2, stdout=devnull, stderr=devnull)  # should extract files fine.
        res = p.wait()
        if (res >= 0 and os.name == 'nt') or res == 0:  # for windows chp returns process id if successful or -1*Error code. Linux returns 0 for successful.
            nzbtomedia.logger.info("EXTRACTOR: Extraction was successful for %s to %s" % (filePath, outputDestination))
            success = 1
        elif len(passwords) > 0:
            nzbtomedia.logger.info("EXTRACTOR: Attempting to extract with passwords")
            for password in passwords:
                if password == "":  # if edited in windows or otherwise if blank lines.
                    continue
                cmd2 = cmd
                #append password here.
                passcmd = "-p" + password
                cmd2.append(passcmd)
                p = Popen(cmd2, stdout=devnull, stderr=devnull)  # should extract files fine.
                res = p.wait()
                if (res >= 0 and platform == 'Windows') or res == 0:
                    nzbtomedia.logger.info("EXTRACTOR: Extraction was successful for %s to %s using password: %s" % (
                    filePath, outputDestination, password))
                    success = 1
                    break
                else:
                    continue
    except:
        nzbtomedia.logger.error("EXTRACTOR: Extraction failed for %s. Could not call command %s" % (filePath, cmd))
        os.chdir(pwd)
        return False

    devnull.close()
    os.chdir(pwd)  # Go back to our Original Working Directory
    if success:
        # sleep to let files finish writing to disk
        sleep (3)
        return True
    else:
        nzbtomedia.logger.error("EXTRACTOR: Extraction failed for %s. Result was %s" % (filePath, res))
        return False
