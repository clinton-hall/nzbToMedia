import ctypes.wintypes

GetModuleFileName = ctypes.windll.kernel32.GetModuleFileNameW
GetModuleFileName.argtypes = (
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.LPWSTR,
    ctypes.wintypes.DWORD,
)
GetModuleFileName.restype = ctypes.wintypes.DWORD
