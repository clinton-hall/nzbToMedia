from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import typing

import nzb2media

if os.name == 'nt':
    # pylint: disable-next=no-name-in-module
    from win32api import CloseHandle
    # pylint: disable-next=no-name-in-module
    from win32api import GetLastError
    # pylint: disable-next=no-name-in-module
    from win32event import CreateMutex
    from winerror import ERROR_ALREADY_EXISTS

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class WindowsProcess:
    def __init__(self):
        self.mutex = None
        # {D0E858DF-985E-4907-B7FB-8D732C3FC3B9}
        _path_str = os.fspath(nzb2media.PID_FILE).replace('\\', '/')
        self.mutexname = f'nzbtomedia_{_path_str}'
        self.create_mutex = CreateMutex
        self.close_handle = CloseHandle
        self.get_last_error = GetLastError
        self.error_already_exists = ERROR_ALREADY_EXISTS

    def alreadyrunning(self):
        self.mutex = self.create_mutex(None, 0, self.mutexname)
        self.lasterror = self.get_last_error()
        if self.lasterror == self.error_already_exists:
            self.close_handle(self.mutex)
            return True
        return False

    def __del__(self):
        if self.mutex:
            self.close_handle(self.mutex)


class PosixProcess:
    def __init__(self):
        self.pidpath = nzb2media.PID_FILE
        self.lock_socket = None

    def alreadyrunning(self):
        try:
            self.lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.lock_socket.bind(f'\0{self.pidpath}')
            self.lasterror = False
            return self.lasterror
        except OSError as error:
            if 'Address already in use' in str(error):
                self.lasterror = True
                return self.lasterror
        except AttributeError:
            pass
        if self.pidpath.exists():
            # Make sure it is not a 'stale' pidFile
            try:
                pid = int(self.pidpath.read_text().strip())
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
            # Write my pid into pidFile to keep multiple copies of program
            # from running
            self.pidpath.write_text(os.getpid())
        return self.lasterror

    def __del__(self):
        if not self.lasterror:
            if self.lock_socket:
                self.lock_socket.close()
            if self.pidpath.is_file():
                self.pidpath.unlink()


# Alternative union syntax using | fails on Python < 3.10
# pylint: disable-next=consider-alternative-union-syntax
ProcessType = typing.Type[typing.Union[PosixProcess, WindowsProcess]]
if os.name == 'nt':
    RunningProcess: ProcessType = WindowsProcess
else:
    RunningProcess = PosixProcess


def restart():
    install_type = nzb2media.version_check.CheckVersion().install_type
    status = 0
    popen_list = []
    if install_type in {'git', 'source'}:
        popen_list = [sys.executable, nzb2media.APP_FILENAME]
    if popen_list:
        popen_list += nzb2media.SYS_ARGV
        log.info(f'Restarting nzbToMedia with {popen_list}')
        with subprocess.Popen(popen_list, cwd=os.getcwd()) as proc:
            proc.wait()
            status = proc.returncode
    os._exit(status)
