from __future__ import with_statement, print_function

import sys
import re
import itertools
from contextlib import contextmanager
import io
import ctypes
from ctypes import windll

import six
from six.moves import map

from jaraco.windows.api import clipboard, memory
from jaraco.windows.error import handle_nonzero_success, WindowsError
from jaraco.windows.memory import LockedMemory

__all__ = (
	'GetClipboardData', 'CloseClipboard',
	'SetClipboardData', 'OpenClipboard',
)


def OpenClipboard(owner=None):
	"""
	Open the clipboard.

	owner
	[in] Handle to the window to be associated with the open clipboard.
	If this parameter is None, the open clipboard is associated with the
	current task.
	"""
	handle_nonzero_success(windll.user32.OpenClipboard(owner))


def CloseClipboard():
	handle_nonzero_success(windll.user32.CloseClipboard())


data_handlers = dict()


def handles(*formats):
	def register(func):
		for format in formats:
			data_handlers[format] = func
		return func
	return register


def nts(buffer):
	"""
	Null Terminated String
	Get the portion of bytestring buffer up to a null character.
	"""
	result, null, rest = buffer.partition('\x00')
	return result


@handles(clipboard.CF_DIBV5, clipboard.CF_DIB)
def raw_data(handle):
	return LockedMemory(handle).data


@handles(clipboard.CF_TEXT)
def text_string(handle):
	return nts(raw_data(handle))


@handles(clipboard.CF_UNICODETEXT)
def unicode_string(handle):
	return nts(raw_data(handle).decode('utf-16'))


@handles(clipboard.CF_BITMAP)
def as_bitmap(handle):
	# handle is HBITMAP
	raise NotImplementedError("Can't convert to DIB")
	# todo: use GetDIBits http://msdn.microsoft.com
	# /en-us/library/dd144879%28v=VS.85%29.aspx


@handles(clipboard.CF_HTML)
class HTMLSnippet(object):
	def __init__(self, handle):
		self.data = nts(raw_data(handle).decode('utf-8'))
		self.headers = self.parse_headers(self.data)

	@property
	def html(self):
		return self.data[self.headers['StartHTML']:]

	@staticmethod
	def parse_headers(data):
		d = io.StringIO(data)

		def header_line(line):
			return re.match('(\w+):(.*)', line)
		headers = map(header_line, d)
		# grab headers until they no longer match
		headers = itertools.takewhile(bool, headers)

		def best_type(value):
			try:
				return int(value)
			except ValueError:
				pass
			try:
				return float(value)
			except ValueError:
				pass
			return value
		pairs = (
			(header.group(1), best_type(header.group(2)))
			for header
			in headers
		)
		return dict(pairs)


def GetClipboardData(type=clipboard.CF_UNICODETEXT):
	if type not in data_handlers:
		raise NotImplementedError("No support for data of type %d" % type)
	handle = clipboard.GetClipboardData(type)
	if handle is None:
		raise TypeError("No clipboard data of type %d" % type)
	return data_handlers[type](handle)


def EmptyClipboard():
	handle_nonzero_success(windll.user32.EmptyClipboard())


def SetClipboardData(type, content):
	"""
	Modeled after http://msdn.microsoft.com
	/en-us/library/ms649016%28VS.85%29.aspx
	#_win32_Copying_Information_to_the_Clipboard
	"""
	allocators = {
		clipboard.CF_TEXT: ctypes.create_string_buffer,
		clipboard.CF_UNICODETEXT: ctypes.create_unicode_buffer,
		clipboard.CF_HTML: ctypes.create_string_buffer,
	}
	if type not in allocators:
		raise NotImplementedError(
			"Only text and HTML types are supported at this time")
	# allocate the memory for the data
	content = allocators[type](content)
	flags = memory.GMEM_MOVEABLE
	size = ctypes.sizeof(content)
	handle_to_copy = windll.kernel32.GlobalAlloc(flags, size)
	with LockedMemory(handle_to_copy) as lm:
		ctypes.memmove(lm.data_ptr, content, size)
	result = clipboard.SetClipboardData(type, handle_to_copy)
	if result is None:
		raise WindowsError()


def set_text(source):
	with context():
		EmptyClipboard()
		SetClipboardData(clipboard.CF_TEXT, source)


def get_text():
	with context():
		result = GetClipboardData(clipboard.CF_TEXT)
	return result


def set_unicode_text(source):
	with context():
		EmptyClipboard()
		SetClipboardData(clipboard.CF_UNICODETEXT, source)


def get_unicode_text():
	with context():
		return GetClipboardData()


def get_html():
	with context():
		result = GetClipboardData(clipboard.CF_HTML)
	return result


def set_html(source):
	with context():
		EmptyClipboard()
		SetClipboardData(clipboard.CF_UNICODETEXT, source)


def get_image():
	with context():
		return GetClipboardData(clipboard.CF_DIB)


def paste_stdout():
	getter = get_unicode_text if six.PY3 else get_text
	sys.stdout.write(getter())


def stdin_copy():
	setter = set_unicode_text if six.PY3 else set_text
	setter(sys.stdin.read())


@contextmanager
def context():
	OpenClipboard()
	try:
		yield
	finally:
		CloseClipboard()


def get_formats():
	with context():
		format_index = 0
		while True:
			format_index = clipboard.EnumClipboardFormats(format_index)
			if format_index == 0:
				break
			yield format_index
