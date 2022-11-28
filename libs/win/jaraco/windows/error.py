import sys
import builtins
import ctypes
import ctypes.wintypes


__import__('jaraco.windows.api.memory')


def format_system_message(errno):
    """
    Call FormatMessage with a system error number to retrieve
    the descriptive error message.
    """
    # first some flags used by FormatMessageW
    ALLOCATE_BUFFER = 0x100
    FROM_SYSTEM = 0x1000

    # Let FormatMessageW allocate the buffer (we'll free it below)
    # Also, let it know we want a system error message.
    flags = ALLOCATE_BUFFER | FROM_SYSTEM
    source = None
    message_id = errno
    language_id = 0
    result_buffer = ctypes.wintypes.LPWSTR()
    buffer_size = 0
    arguments = None
    bytes = ctypes.windll.kernel32.FormatMessageW(
        flags,
        source,
        message_id,
        language_id,
        ctypes.byref(result_buffer),
        buffer_size,
        arguments,
    )
    # note the following will cause an infinite loop if GetLastError
    #  repeatedly returns an error that cannot be formatted, although
    #  this should not happen.
    handle_nonzero_success(bytes)
    message = result_buffer.value
    ctypes.windll.kernel32.LocalFree(result_buffer)
    return message


class WindowsError(builtins.WindowsError):
    """
    More info about errors at
    http://msdn.microsoft.com/en-us/library/ms681381(VS.85).aspx
    """

    def __init__(self, value=None):
        if value is None:
            value = ctypes.windll.kernel32.GetLastError()
        strerror = format_system_message(value)
        if sys.version_info > (3, 3):
            args = 0, strerror, None, value
        else:
            args = value, strerror
        super(WindowsError, self).__init__(*args)

    @property
    def message(self):
        return self.strerror

    @property
    def code(self):
        return self.winerror

    def __str__(self):
        return self.message

    def __repr__(self):
        return '{self.__class__.__name__}({self.winerror})'.format(**vars())


def handle_nonzero_success(result):
    if result == 0:
        raise WindowsError()
