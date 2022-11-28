from ctypes import windll, POINTER
from ctypes.wintypes import LPWSTR, DWORD, LPVOID, HANDLE, BOOL

CreateEvent = windll.kernel32.CreateEventW
CreateEvent.argtypes = (LPVOID, BOOL, BOOL, LPWSTR)  # LPSECURITY_ATTRIBUTES
CreateEvent.restype = HANDLE

SetEvent = windll.kernel32.SetEvent
SetEvent.argtypes = (HANDLE,)
SetEvent.restype = BOOL

WaitForSingleObject = windll.kernel32.WaitForSingleObject
WaitForSingleObject.argtypes = HANDLE, DWORD
WaitForSingleObject.restype = DWORD

_WaitForMultipleObjects = windll.kernel32.WaitForMultipleObjects
_WaitForMultipleObjects.argtypes = DWORD, POINTER(HANDLE), BOOL, DWORD
_WaitForMultipleObjects.restype = DWORD


def WaitForMultipleObjects(handles, wait_all=False, timeout=0):
    n_handles = len(handles)
    handle_array = (HANDLE * n_handles)()
    for index, handle in enumerate(handles):
        handle_array[index] = handle
    return _WaitForMultipleObjects(n_handles, handle_array, wait_all, timeout)


WAIT_OBJECT_0 = 0
INFINITE = -1
WAIT_TIMEOUT = 0x102
