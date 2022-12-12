import ctypes.wintypes

try:
    from ctypes.wintypes import LPDWORD
except ImportError:
    LPDWORD = ctypes.POINTER(ctypes.wintypes.DWORD)  # type: ignore

GetUserName = ctypes.windll.advapi32.GetUserNameW
GetUserName.argtypes = ctypes.wintypes.LPWSTR, LPDWORD
GetUserName.restype = ctypes.wintypes.DWORD
