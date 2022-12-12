import ctypes.wintypes


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = (
        ('ac_line_status', ctypes.wintypes.BYTE),
        ('battery_flag', ctypes.wintypes.BYTE),
        ('battery_life_percent', ctypes.wintypes.BYTE),
        ('reserved', ctypes.wintypes.BYTE),
        ('battery_life_time', ctypes.wintypes.DWORD),
        ('battery_full_life_time', ctypes.wintypes.DWORD),
    )

    @property
    def ac_line_status_string(self):
        return {0: 'offline', 1: 'online', 255: 'unknown'}[self.ac_line_status]


LPSYSTEM_POWER_STATUS = ctypes.POINTER(SYSTEM_POWER_STATUS)
GetSystemPowerStatus = ctypes.windll.kernel32.GetSystemPowerStatus
GetSystemPowerStatus.argtypes = (LPSYSTEM_POWER_STATUS,)
GetSystemPowerStatus.restype = ctypes.wintypes.BOOL

SetThreadExecutionState = ctypes.windll.kernel32.SetThreadExecutionState
SetThreadExecutionState.argtypes = [ctypes.c_uint]
SetThreadExecutionState.restype = ctypes.c_uint


class ES:
    """
    Execution state constants
    """

    continuous = 0x80000000
    system_required = 1
    display_required = 2
    awaymode_required = 0x40
