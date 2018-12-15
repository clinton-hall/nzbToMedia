import ctypes

from .api import library


def find_lib(lib):
	r"""
	Find the DLL for a given library.

	Accepts a string or loaded module

	>>> print(find_lib('kernel32').lower())
	c:\windows\system32\kernel32.dll
	"""
	if isinstance(lib, str):
		lib = getattr(ctypes.windll, lib)

	size = 1024
	result = ctypes.create_unicode_buffer(size)
	library.GetModuleFileName(lib._handle, result, size)
	return result.value
