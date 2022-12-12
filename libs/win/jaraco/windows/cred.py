import ctypes

import jaraco.windows.api.credential as api
from . import error

CRED_TYPE_GENERIC = 1


def CredDelete(TargetName, Type, Flags=0):
    error.handle_nonzero_success(api.CredDelete(TargetName, Type, Flags))


def CredRead(TargetName, Type, Flags=0):
    cred_pointer = api.PCREDENTIAL()
    res = api.CredRead(TargetName, Type, Flags, ctypes.byref(cred_pointer))
    error.handle_nonzero_success(res)
    return cred_pointer.contents


def CredWrite(Credential, Flags=0):
    res = api.CredWrite(Credential, Flags)
    error.handle_nonzero_success(res)
