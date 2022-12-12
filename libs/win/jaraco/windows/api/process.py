import ctypes.wintypes

TOKEN_ALL_ACCESS = 0xF01FF

GetCurrentProcess = ctypes.windll.kernel32.GetCurrentProcess
GetCurrentProcess.restype = ctypes.wintypes.HANDLE
OpenProcessToken = ctypes.windll.advapi32.OpenProcessToken
OpenProcessToken.argtypes = (
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.DWORD,
    ctypes.POINTER(ctypes.wintypes.HANDLE),
)
OpenProcessToken.restype = ctypes.wintypes.BOOL
