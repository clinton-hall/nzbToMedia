import subprocess
import itertools

from more_itertools import consume, always_iterable


def extract_environment(env_cmd, initial=None):
    """
    Take a command (either a single command or list of arguments)
    and return the environment created after running that command.
    Note that if the command must be a batch file or .cmd file, or the
    changes to the environment will not be captured.

    If initial is supplied, it is used as the initial environment passed
    to the child process.
    """
    # construct the command that will alter the environment
    env_cmd = subprocess.list2cmdline(always_iterable(env_cmd))
    # create a tag so we can tell in the output when the proc is done
    tag = 'Done running command'
    # construct a cmd.exe command to do accomplish this
    cmd = 'cmd.exe /s /c "{env_cmd} && echo "{tag}" && set"'.format(**vars())
    # launch the process
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=initial)
    # parse the output sent to stdout
    lines = proc.stdout
    # make sure the lines are strings

    def make_str(s):
        return s.decode()

    lines = map(make_str, lines)
    # consume whatever output occurs until the tag is reached
    consume(itertools.takewhile(lambda l: tag not in l, lines))
    # construct a dictionary of the pairs
    result = dict(line.rstrip().split('=', 1) for line in lines)
    # let the process finish
    proc.communicate()
    return result
