import ctypes.wintypes

SetEnvironmentVariable = ctypes.windll.kernel32.SetEnvironmentVariableW
SetEnvironmentVariable.restype = ctypes.wintypes.BOOL
SetEnvironmentVariable.argtypes = [ctypes.wintypes.LPCWSTR] * 2

GetEnvironmentVariable = ctypes.windll.kernel32.GetEnvironmentVariableW
GetEnvironmentVariable.restype = ctypes.wintypes.BOOL
GetEnvironmentVariable.argtypes = [
    ctypes.wintypes.LPCWSTR,
    ctypes.wintypes.LPWSTR,
    ctypes.wintypes.DWORD,
]
