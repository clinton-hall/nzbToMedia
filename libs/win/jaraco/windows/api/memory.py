import ctypes.wintypes

GMEM_MOVEABLE = 0x2

GlobalAlloc = ctypes.windll.kernel32.GlobalAlloc
GlobalAlloc.argtypes = ctypes.wintypes.UINT, ctypes.c_size_t
GlobalAlloc.restype = ctypes.wintypes.HANDLE

GlobalLock = ctypes.windll.kernel32.GlobalLock
GlobalLock.argtypes = (ctypes.wintypes.HGLOBAL,)
GlobalLock.restype = ctypes.wintypes.LPVOID

GlobalUnlock = ctypes.windll.kernel32.GlobalUnlock
GlobalUnlock.argtypes = (ctypes.wintypes.HGLOBAL,)
GlobalUnlock.restype = ctypes.wintypes.BOOL

GlobalSize = ctypes.windll.kernel32.GlobalSize
GlobalSize.argtypes = (ctypes.wintypes.HGLOBAL,)
GlobalSize.restype = ctypes.c_size_t

CreateFileMapping = ctypes.windll.kernel32.CreateFileMappingW
CreateFileMapping.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.LPWSTR,
]
CreateFileMapping.restype = ctypes.wintypes.HANDLE

MapViewOfFile = ctypes.windll.kernel32.MapViewOfFile
MapViewOfFile.restype = ctypes.wintypes.HANDLE

UnmapViewOfFile = ctypes.windll.kernel32.UnmapViewOfFile
UnmapViewOfFile.argtypes = (ctypes.wintypes.HANDLE,)

RtlMoveMemory = ctypes.windll.kernel32.RtlMoveMemory
RtlMoveMemory.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t)

ctypes.windll.kernel32.LocalFree.argtypes = (ctypes.wintypes.HLOCAL,)
