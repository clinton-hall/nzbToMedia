"""
Support for Credential Vault
"""

import ctypes
from ctypes.wintypes import DWORD, LPCWSTR, BOOL, LPWSTR, FILETIME


try:
    from ctypes.wintypes import LPBYTE
except ImportError:
    LPBYTE = ctypes.POINTER(ctypes.wintypes.BYTE)  # type: ignore


class CredentialAttribute(ctypes.Structure):
    _fields_ = []  # type: ignore


class Credential(ctypes.Structure):
    _fields_ = [
        ('flags', DWORD),
        ('type', DWORD),
        ('target_name', LPWSTR),
        ('comment', LPWSTR),
        ('last_written', FILETIME),
        ('credential_blob_size', DWORD),
        ('credential_blob', LPBYTE),
        ('persist', DWORD),
        ('attribute_count', DWORD),
        ('attributes', ctypes.POINTER(CredentialAttribute)),
        ('target_alias', LPWSTR),
        ('user_name', LPWSTR),
    ]

    def __del__(self):
        ctypes.windll.advapi32.CredFree(ctypes.byref(self))


PCREDENTIAL = ctypes.POINTER(Credential)

CredRead = ctypes.windll.advapi32.CredReadW
CredRead.argtypes = (
    LPCWSTR,  # TargetName
    DWORD,  # Type
    DWORD,  # Flags
    ctypes.POINTER(PCREDENTIAL),  # Credential
)
CredRead.restype = BOOL

CredWrite = ctypes.windll.advapi32.CredWriteW
CredWrite.argtypes = (PCREDENTIAL, DWORD)  # Credential  # Flags
CredWrite.restype = BOOL

CredDelete = ctypes.windll.advapi32.CredDeleteW
CredDelete.argtypes = (LPCWSTR, DWORD, DWORD)  # TargetName  # Type  # Flags
CredDelete.restype = BOOL
