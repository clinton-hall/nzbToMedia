import ctypes
from .api import errors
from .api.user import GetUserName
from .error import WindowsError, handle_nonzero_success


def get_user_name():
	size = ctypes.wintypes.DWORD()
	try:
		handle_nonzero_success(GetUserName(None, size))
	except WindowsError as e:
		if e.code != errors.ERROR_INSUFFICIENT_BUFFER:
			raise
	buffer = ctypes.create_unicode_buffer(size.value)
	handle_nonzero_success(GetUserName(buffer, size))
	return buffer.value
