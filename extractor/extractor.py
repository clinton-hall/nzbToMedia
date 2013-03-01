import os
import sys
import logging
from subprocess import call

Logger = logging.getLogger()

# which() and os_platform() breaks when running in Transmission (has to do with os.environ)

def os_platform():
    # Author Credit: Matthew Scouten @ http://stackoverflow.com/a/7260315
    true_platform = os.environ['PROCESSOR_ARCHITECTURE']
    try:
            true_platform = os.environ["PROCESSOR_ARCHITEW6432"]
    except KeyError:
            pass
            #true_platform not assigned to if this does not exist
    return true_platform

def which(program):
    # Author Credit: Jay @ http://stackoverflow.com/a/377028
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def extract(dirpath, file, outputDestination):
    # Using Windows
    if os.name == 'nt':
        if os_platform() == 'AMD64':
            platform = 'x64'
        else:
            platform = 'x86'
        if not os.path.dirname(sys.argv[0]):
            sevenzipLocation = os.path.normpath(os.path.join(os.getcwd(), 'extractor/bin/' + platform + '/7z.exe'))
        else:
            sevenzipLocation = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), 'extractor/bin/' + platform + '/7z.exe'))
        if not os.path.exists(sevenzipLocation):
            Logger.error("EXTRACTOR: Couldnt find 7-zip, Exiting")
            sys.exit(-1)
        else:
            cmd_7zip = [sevenzipLocation, 'x -y']
            ext_7zip = [".rar",".zip",".tar.gz","tgz",".tar.bz2",".tbz",".tar.lzma",".tlz",".7z",".xz"]
            EXTRACT_COMMANDS = dict.fromkeys(ext_7zip, cmd_7zip)
    # Using unix
    else:
        required_cmds=["unrar", "unzip", "tar", "unxz", "unlzma", "7zr", "bunzip2"]
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
            for cmd in required_cmds:
                if call(['which', cmd]): #note, returns 0 if exists, or 1 if doesn't exist.
                    for k, v in EXTRACT_COMMANDS.items():
                        if cmd in v[0]:
                            Logger.error("EXTRACTOR: %s not found, disabling support for %s", cmd, k)
                            del EXTRACT_COMMANDS[k]
        else:
            Logger.warn("EXTRACTOR: Cannot determine which tool to use when called from Transmission")

        if not EXTRACT_COMMANDS:
            Logger.warn("EXTRACTOR: No archive extracting programs found, plugin will be disabled")

    ext = os.path.splitext(file)
    filePath = os.path.join(dirpath, file)
    if ext[1] in (".gz", ".bz2", ".lzma"):
    # Check if this is a tar
        if os.path.splitext(ext[0])[1] == ".tar":
            cmd = EXTRACT_COMMANDS[".tar" + ext[1]]
    else:
        if ext[1] in EXTRACT_COMMANDS:
            cmd = EXTRACT_COMMANDS[ext[1]]
        else:
            Logger.debug("EXTRACTOR: Unknown file type: %s", ext[1])
            return False

    # Create outputDestination folder
    if not os.path.exists(outputDestination):
        try:
            Logger.debug("EXTRACTOR: Creating destination folder: %s", outputDestination)
            os.makedirs(outputDestination)
        except Exception, e:
            Logger.error("EXTRACTOR: Not possible to create destination folder: %s", e)
            return False
    Logger.info("Extracting %s to %s", filePath, outputDestination)
    Logger.debug("Extracting %s %s %s %s", cmd[0], cmd[1], filePath, outputDestination)
    pwd = os.getcwd() # Get our Present Working Directory
    os.chdir(outputDestination) # Not all unpack commands accept full paths, so just extract into this directory
    if os.name == 'nt': # Windows needs quotes around directory structure
        try:
            run = "\"" + cmd[0] + "\" " + cmd[1] + " \"" + filePath + "\"" # Windows needs quotes around directories
            res = call(run)
            if res == 0:
                Logger.info("EXTRACTOR: Extraction was successful for %s to %s", filePath, outputDestination)
            else:
                Logger.info("EXTRACTOR: Extraction failed for %s. 7zip result was %s", filePath, res)
        except:
            Logger.error("EXTRACTOR: Extraction failed for %s. Could not call command %s", filePath, run)
    else:
        try:
            x = len(cmd)
            cmd[x] = filePath # add filePath to final cmd arg
            res = call(cmd) # 
            if res == 0:
                Logger.info("EXTRACTOR: Extraction was successful for %s to %s", filePath, outputDestination)
            else:
                Logger.error("EXTRACTOR: Extraction failed for %s. 7zip result was %s", filePath, res)
        except:
            Logger.error("EXTRACTOR: Extraction failed for %s. Could not call command %s %s %s %s", filePath, cmd[0], cmd[1], filePath) 
    os.chdir(pwd) # Go back to our Original Working Directory
    return True
