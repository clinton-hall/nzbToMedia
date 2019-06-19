from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
import socket
import subprocess
import sys

import core
from core import logger, version_check, APP_FILENAME, SYS_ARGV

if os.name == 'nt':
    from win32event import CreateMutex
    from win32api import CloseHandle, GetLastError
    from winerror import ERROR_ALREADY_EXISTS


class WindowsProcess(object):
    def __init__(self):
        self.mutex = None
        self.mutexname = 'nzbtomedia_{pid}'.format(pid=core.PID_FILE.replace('\\', '/'))  # {D0E858DF-985E-4907-B7FB-8D732C3FC3B9}'
        self.CreateMutex = CreateMutex
        self.CloseHandle = CloseHandle
        self.GetLastError = GetLastError
        self.ERROR_ALREADY_EXISTS = ERROR_ALREADY_EXISTS

    def alreadyrunning(self):
        self.mutex = self.CreateMutex(None, 0, self.mutexname)
        self.lasterror = self.GetLastError()
        if self.lasterror == self.ERROR_ALREADY_EXISTS:
            self.CloseHandle(self.mutex)
            return True
        else:
            return False

    def __del__(self):
        if self.mutex:
            self.CloseHandle(self.mutex)


class PosixProcess(object):
    def __init__(self):
        self.pidpath = core.PID_FILE
        self.lock_socket = None

    def alreadyrunning(self):
        try:
            self.lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.lock_socket.bind('\0{path}'.format(path=self.pidpath))
            self.lasterror = False
            return self.lasterror
        except socket.error as e:
            if 'Address already in use' in str(e):
                self.lasterror = True
                return self.lasterror
        except AttributeError:
            pass
        if os.path.exists(self.pidpath):
            # Make sure it is not a 'stale' pidFile
            try:
                pid = int(open(self.pidpath, 'r').read().strip())
            except Exception:
                pid = None
            # Check list of running pids, if not running it is stale so overwrite
            if isinstance(pid, int):
                try:
                    os.kill(pid, 0)
                    self.lasterror = True
                except OSError:
                    self.lasterror = False
            else:
                self.lasterror = False
        else:
            self.lasterror = False

        if not self.lasterror:
            # Write my pid into pidFile to keep multiple copies of program from running
            try:
                fp = open(self.pidpath, 'w')
                fp.write(str(os.getpid()))
                fp.close()
            except Exception:
                pass

        return self.lasterror

    def __del__(self):
        if not self.lasterror:
            if self.lock_socket:
                self.lock_socket.close()
            if os.path.isfile(self.pidpath):
                os.unlink(self.pidpath)


if os.name == 'nt':
    RunningProcess = WindowsProcess
else:
    RunningProcess = PosixProcess


def restart():
    install_type = version_check.CheckVersion().install_type

    status = 0
    popen_list = []

    if install_type in ('git', 'source'):
        popen_list = [sys.executable, APP_FILENAME]

    if popen_list:
        popen_list += SYS_ARGV
        logger.log(u'Restarting nzbToMedia with {args}'.format(args=popen_list))
        logger.close()
        p = subprocess.Popen(popen_list, cwd=os.getcwd())
        p.wait()
        status = p.returncode

    os._exit(status)
