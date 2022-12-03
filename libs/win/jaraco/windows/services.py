"""
Windows Services support for controlling Windows Services.

Based on http://code.activestate.com
/recipes/115875-controlling-windows-services/
"""

import sys
import time

import win32api
import win32con
import win32service


class Service(object):
    """
    The Service Class is used for controlling Windows
    services. Just pass the name of the service you wish to control to the
    class instance and go from there. For example, if you want to control
    the Workstation service try this:

        from jaraco.windows import services
        workstation = services.Service("Workstation")
        workstation.start()
        workstation.fetchstatus("running", 10)
        workstation.stop()
        workstation.fetchstatus("stopped")

    Creating an instance of the Service class is done by passing the name of
    the service as it appears in the Management Console or the short name as
    it appears in the registry. Mixed case is ok.
        cvs = services.Service("CVS NT Service 1.11.1.2 (Build 41)")
            or
        cvs = services.Service("cvs")

    If needing remote service control try this:
        cvs = services.Service("cvs", r"\\CVS_SERVER")
            or
        cvs = services.Service("cvs", "\\\\CVS_SERVER")

    The Service Class supports these methods:

        start: Starts service.
        stop: Stops service.
        restart: Stops and restarts service.
        pause: Pauses service (Only if service supports feature).
        resume: Resumes service that has been paused.
        status: Queries current status of service.
        fetchstatus: Continually queries service until requested
            status(STARTING, RUNNING,
            STOPPING & STOPPED) is met or timeout value(in seconds) reached.
            Default timeout value is infinite.
        infotype: Queries service for process type. (Single, shared and/or
            interactive process)
        infoctrl: Queries control information about a running service.
            i.e. Can it be paused, stopped, etc?
        infostartup: Queries service Startup type. (Boot, System,
            Automatic, Manual, Disabled)
        setstartup: Changes/sets Startup type. (Boot, System,
            Automatic, Manual, Disabled)
        getname: Gets the long and short service names used by Windowin32service.
            (Generally used for internal purposes)
    """

    def __init__(self, service, machinename=None, dbname=None):
        self.userv = service
        self.scmhandle = win32service.OpenSCManager(
            machinename, dbname, win32service.SC_MANAGER_ALL_ACCESS
        )
        self.sserv, self.lserv = self.getname()
        if (self.sserv or self.lserv) is None:
            sys.exit()
        self.handle = win32service.OpenService(
            self.scmhandle, self.sserv, win32service.SERVICE_ALL_ACCESS
        )
        self.sccss = "SYSTEM\\CurrentControlSet\\Services\\"

    def start(self):
        win32service.StartService(self.handle, None)

    def stop(self):
        self.stat = win32service.ControlService(
            self.handle, win32service.SERVICE_CONTROL_STOP
        )

    def restart(self):
        self.stop()
        self.fetchstatus("STOPPED")
        self.start()

    def pause(self):
        self.stat = win32service.ControlService(
            self.handle, win32service.SERVICE_CONTROL_PAUSE
        )

    def resume(self):
        self.stat = win32service.ControlService(
            self.handle, win32service.SERVICE_CONTROL_CONTINUE
        )

    def status(self, prn=0):
        self.stat = win32service.QueryServiceStatus(self.handle)
        if self.stat[1] == win32service.SERVICE_STOPPED:
            if prn == 1:
                print("The %s service is stopped." % self.lserv)
            else:
                return "STOPPED"
        elif self.stat[1] == win32service.SERVICE_START_PENDING:
            if prn == 1:
                print("The %s service is starting." % self.lserv)
            else:
                return "STARTING"
        elif self.stat[1] == win32service.SERVICE_STOP_PENDING:
            if prn == 1:
                print("The %s service is stopping." % self.lserv)
            else:
                return "STOPPING"
        elif self.stat[1] == win32service.SERVICE_RUNNING:
            if prn == 1:
                print("The %s service is running." % self.lserv)
            else:
                return "RUNNING"

    def fetchstatus(self, fstatus, timeout=None):
        self.fstatus = fstatus.upper()
        if timeout is not None:
            timeout = int(timeout)
            timeout *= 2

        def to(timeout):
            time.sleep(0.5)
            if timeout is not None:
                if timeout > 1:
                    timeout -= 1
                    return timeout
                else:
                    return "TO"

        if self.fstatus == "STOPPED":
            while 1:
                self.stat = win32service.QueryServiceStatus(self.handle)
                if self.stat[1] == win32service.SERVICE_STOPPED:
                    self.fstate = "STOPPED"
                    break
                else:
                    timeout = to(timeout)
                    if timeout == "TO":
                        return "TIMEDOUT"
                        break
        elif self.fstatus == "STOPPING":
            while 1:
                self.stat = win32service.QueryServiceStatus(self.handle)
                if self.stat[1] == win32service.SERVICE_STOP_PENDING:
                    self.fstate = "STOPPING"
                    break
                else:
                    timeout = to(timeout)
                    if timeout == "TO":
                        return "TIMEDOUT"
                        break
        elif self.fstatus == "RUNNING":
            while 1:
                self.stat = win32service.QueryServiceStatus(self.handle)
                if self.stat[1] == win32service.SERVICE_RUNNING:
                    self.fstate = "RUNNING"
                    break
                else:
                    timeout = to(timeout)
                    if timeout == "TO":
                        return "TIMEDOUT"
                        break
        elif self.fstatus == "STARTING":
            while 1:
                self.stat = win32service.QueryServiceStatus(self.handle)
                if self.stat[1] == win32service.SERVICE_START_PENDING:
                    self.fstate = "STARTING"
                    break
                else:
                    timeout = to(timeout)
                    if timeout == "TO":
                        return "TIMEDOUT"
                        break

    def infotype(self):
        self.stat = win32service.QueryServiceStatus(self.handle)
        if self.stat[0] and win32service.SERVICE_WIN32_OWN_PROCESS:
            print("The %s service runs in its own process." % self.lserv)
        if self.stat[0] and win32service.SERVICE_WIN32_SHARE_PROCESS:
            print("The %s service shares a process with other services." % self.lserv)
        if self.stat[0] and win32service.SERVICE_INTERACTIVE_PROCESS:
            print("The %s service can interact with the desktop." % self.lserv)

    def infoctrl(self):
        self.stat = win32service.QueryServiceStatus(self.handle)
        if self.stat[2] and win32service.SERVICE_ACCEPT_PAUSE_CONTINUE:
            print("The %s service can be paused." % self.lserv)
        if self.stat[2] and win32service.SERVICE_ACCEPT_STOP:
            print("The %s service can be stopped." % self.lserv)
        if self.stat[2] and win32service.SERVICE_ACCEPT_SHUTDOWN:
            print("The %s service can be shutdown." % self.lserv)

    def infostartup(self):
        self.isuphandle = win32api.RegOpenKeyEx(
            win32con.HKEY_LOCAL_MACHINE, self.sccss + self.sserv, 0, win32con.KEY_READ
        )
        self.isuptype = win32api.RegQueryValueEx(self.isuphandle, "Start")[0]
        win32api.RegCloseKey(self.isuphandle)
        if self.isuptype == 0:
            return "boot"
        elif self.isuptype == 1:
            return "system"
        elif self.isuptype == 2:
            return "automatic"
        elif self.isuptype == 3:
            return "manual"
        elif self.isuptype == 4:
            return "disabled"

    @property
    def suptype(self):
        types = 'boot', 'system', 'automatic', 'manual', 'disabled'
        lookup = dict((name, number) for number, name in enumerate(types))
        return lookup[self.startuptype]

    def setstartup(self, startuptype):
        self.startuptype = startuptype.lower()
        self.snc = win32service.SERVICE_NO_CHANGE
        win32service.ChangeServiceConfig(
            self.handle,
            self.snc,
            self.suptype,
            self.snc,
            None,
            None,
            0,
            None,
            None,
            None,
            self.lserv,
        )

    def getname(self):
        self.snames = win32service.EnumServicesStatus(self.scmhandle)
        for i in self.snames:
            if i[0].lower() == self.userv.lower():
                return i[0], i[1]
                break
            if i[1].lower() == self.userv.lower():
                return i[0], i[1]
                break
        print("Error: The %s service doesn't seem to exist." % self.userv)
        return None, None
