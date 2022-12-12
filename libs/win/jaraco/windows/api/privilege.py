import ctypes.wintypes


class LUID(ctypes.Structure):
    _fields_ = [
        ('low_part', ctypes.wintypes.DWORD),
        ('high_part', ctypes.wintypes.LONG),
    ]

    def __eq__(self, other):
        return self.high_part == other.high_part and self.low_part == other.low_part

    def __ne__(self, other):
        return not (self == other)


LookupPrivilegeValue = ctypes.windll.advapi32.LookupPrivilegeValueW
LookupPrivilegeValue.argtypes = (
    ctypes.wintypes.LPWSTR,  # system name
    ctypes.wintypes.LPWSTR,  # name
    ctypes.POINTER(LUID),
)
LookupPrivilegeValue.restype = ctypes.wintypes.BOOL


class TOKEN_INFORMATION_CLASS:
    TokenUser = 1
    TokenGroups = 2
    TokenPrivileges = 3
    # ... see http://msdn.microsoft.com/en-us/library/aa379626%28VS.85%29.aspx


SE_PRIVILEGE_ENABLED_BY_DEFAULT = 0x00000001
SE_PRIVILEGE_ENABLED = 0x00000002
SE_PRIVILEGE_REMOVED = 0x00000004
SE_PRIVILEGE_USED_FOR_ACCESS = 0x80000000


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('LUID', LUID), ('attributes', ctypes.wintypes.DWORD)]

    def is_enabled(self):
        return bool(self.attributes & SE_PRIVILEGE_ENABLED)

    def enable(self):
        self.attributes |= SE_PRIVILEGE_ENABLED

    def get_name(self):
        size = ctypes.wintypes.DWORD(10240)
        buf = ctypes.create_unicode_buffer(size.value)
        res = LookupPrivilegeName(None, self.LUID, buf, size)
        if res == 0:
            raise RuntimeError
        return buf[: size.value]

    def __str__(self):
        res = self.get_name()
        if self.is_enabled():
            res += ' (enabled)'
        return res


LookupPrivilegeName = ctypes.windll.advapi32.LookupPrivilegeNameW
LookupPrivilegeName.argtypes = (
    ctypes.wintypes.LPWSTR,  # lpSystemName
    ctypes.POINTER(LUID),  # lpLuid
    ctypes.wintypes.LPWSTR,  # lpName
    ctypes.POINTER(ctypes.wintypes.DWORD),  # cchName
)
LookupPrivilegeName.restype = ctypes.wintypes.BOOL


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [
        ('count', ctypes.wintypes.DWORD),
        ('privileges', LUID_AND_ATTRIBUTES * 0),
    ]

    def get_array(self):
        array_type = LUID_AND_ATTRIBUTES * self.count
        privileges = ctypes.cast(self.privileges, ctypes.POINTER(array_type)).contents
        return privileges

    def __iter__(self):
        return iter(self.get_array())


PTOKEN_PRIVILEGES = ctypes.POINTER(TOKEN_PRIVILEGES)

GetTokenInformation = ctypes.windll.advapi32.GetTokenInformation
GetTokenInformation.argtypes = [
    ctypes.wintypes.HANDLE,  # TokenHandle
    ctypes.c_uint,  # TOKEN_INFORMATION_CLASS value
    ctypes.c_void_p,  # TokenInformation
    ctypes.wintypes.DWORD,  # TokenInformationLength
    ctypes.POINTER(ctypes.wintypes.DWORD),  # ReturnLength
]
GetTokenInformation.restype = ctypes.wintypes.BOOL

# http://msdn.microsoft.com/en-us/library/aa375202%28VS.85%29.aspx
AdjustTokenPrivileges = ctypes.windll.advapi32.AdjustTokenPrivileges
AdjustTokenPrivileges.restype = ctypes.wintypes.BOOL
AdjustTokenPrivileges.argtypes = [
    ctypes.wintypes.HANDLE,  # TokenHandle
    ctypes.wintypes.BOOL,  # DisableAllPrivileges
    PTOKEN_PRIVILEGES,  # NewState (optional)
    ctypes.wintypes.DWORD,  # BufferLength of PreviousState
    PTOKEN_PRIVILEGES,  # PreviousState (out, optional)
    ctypes.POINTER(ctypes.wintypes.DWORD),  # ReturnLength
]
