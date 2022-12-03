import ctypes.wintypes

from jaraco.windows.error import handle_nonzero_success
from .api import security


def GetTokenInformation(token, information_class):
    """
    Given a token, get the token information for it.
    """
    data_size = ctypes.wintypes.DWORD()
    ctypes.windll.advapi32.GetTokenInformation(
        token, information_class.num, 0, 0, ctypes.byref(data_size)
    )
    data = ctypes.create_string_buffer(data_size.value)
    handle_nonzero_success(
        ctypes.windll.advapi32.GetTokenInformation(
            token,
            information_class.num,
            ctypes.byref(data),
            ctypes.sizeof(data),
            ctypes.byref(data_size),
        )
    )
    return ctypes.cast(data, ctypes.POINTER(security.TOKEN_USER)).contents


def OpenProcessToken(proc_handle, access):
    result = ctypes.wintypes.HANDLE()
    proc_handle = ctypes.wintypes.HANDLE(proc_handle)
    handle_nonzero_success(
        ctypes.windll.advapi32.OpenProcessToken(
            proc_handle, access, ctypes.byref(result)
        )
    )
    return result


def get_current_user():
    """
    Return a TOKEN_USER for the owner of this process.
    """
    process = OpenProcessToken(
        ctypes.windll.kernel32.GetCurrentProcess(), security.TokenAccess.TOKEN_QUERY
    )
    return GetTokenInformation(process, security.TOKEN_USER)


def get_security_attributes_for_user(user=None):
    """
    Return a SECURITY_ATTRIBUTES structure with the SID set to the
    specified user (uses current user if none is specified).
    """
    if user is None:
        user = get_current_user()

    assert isinstance(user, security.TOKEN_USER), "user must be TOKEN_USER instance"

    SD = security.SECURITY_DESCRIPTOR()
    SA = security.SECURITY_ATTRIBUTES()
    # by attaching the actual security descriptor, it will be garbage-
    # collected with the security attributes
    SA.descriptor = SD
    SA.bInheritHandle = 1

    ctypes.windll.advapi32.InitializeSecurityDescriptor(
        ctypes.byref(SD), security.SECURITY_DESCRIPTOR.REVISION
    )
    ctypes.windll.advapi32.SetSecurityDescriptorOwner(ctypes.byref(SD), user.SID, 0)
    return SA
