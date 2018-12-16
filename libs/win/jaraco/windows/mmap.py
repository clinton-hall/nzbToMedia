import ctypes.wintypes

import six

from .error import handle_nonzero_success
from .api import memory


class MemoryMap(object):
	"""
	A memory map object which can have security attributes overridden.
	"""
	def __init__(self, name, length, security_attributes=None):
		self.name = name
		self.length = length
		self.security_attributes = security_attributes
		self.pos = 0

	def __enter__(self):
		p_SA = (
			ctypes.byref(self.security_attributes)
			if self.security_attributes else None
		)
		INVALID_HANDLE_VALUE = -1
		PAGE_READWRITE = 0x4
		FILE_MAP_WRITE = 0x2
		filemap = ctypes.windll.kernel32.CreateFileMappingW(
			INVALID_HANDLE_VALUE, p_SA, PAGE_READWRITE, 0, self.length,
			six.text_type(self.name))
		handle_nonzero_success(filemap)
		if filemap == INVALID_HANDLE_VALUE:
			raise Exception("Failed to create file mapping")
		self.filemap = filemap
		self.view = memory.MapViewOfFile(filemap, FILE_MAP_WRITE, 0, 0, 0)
		return self

	def seek(self, pos):
		self.pos = pos

	def write(self, msg):
		assert isinstance(msg, bytes)
		n = len(msg)
		if self.pos + n >= self.length:  # A little safety.
			raise ValueError("Refusing to write %d bytes" % n)
		dest = self.view + self.pos
		length = ctypes.c_size_t(n)
		ctypes.windll.kernel32.RtlMoveMemory(dest, msg, length)
		self.pos += n

	def read(self, n):
		"""
		Read n bytes from mapped view.
		"""
		out = ctypes.create_string_buffer(n)
		source = self.view + self.pos
		length = ctypes.c_size_t(n)
		ctypes.windll.kernel32.RtlMoveMemory(out, source, length)
		self.pos += n
		return out.raw

	def __exit__(self, exc_type, exc_val, tb):
		ctypes.windll.kernel32.UnmapViewOfFile(self.view)
		ctypes.windll.kernel32.CloseHandle(self.filemap)
