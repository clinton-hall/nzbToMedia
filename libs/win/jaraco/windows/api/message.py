#!/usr/bin/env python

"""
jaraco.windows.message

Windows Messaging support
"""

import ctypes
from ctypes.wintypes import HWND, UINT, WPARAM, LPARAM, DWORD, LPVOID

import six

LRESULT = LPARAM


class LPARAM_wstr(LPARAM):
	"""
	A special instance of LPARAM that can be constructed from a string
	instance (for functions such as SendMessage, whose LPARAM may point to
	a unicode string).
	"""
	@classmethod
	def from_param(cls, param):
		if isinstance(param, six.string_types):
			return LPVOID.from_param(six.text_type(param))
		return LPARAM.from_param(param)


SendMessage = ctypes.windll.user32.SendMessageW
SendMessage.argtypes = (HWND, UINT, WPARAM, LPARAM_wstr)
SendMessage.restype = LRESULT

HWND_BROADCAST = 0xFFFF
WM_SETTINGCHANGE = 0x1A

# constants from http://msdn.microsoft.com
# /en-us/library/ms644952%28v=vs.85%29.aspx
SMTO_ABORTIFHUNG = 0x02
SMTO_BLOCK = 0x01
SMTO_NORMAL = 0x00
SMTO_NOTIMEOUTIFNOTHUNG = 0x08
SMTO_ERRORONEXIT = 0x20

SendMessageTimeout = ctypes.windll.user32.SendMessageTimeoutW
SendMessageTimeout.argtypes = SendMessage.argtypes + (
	UINT, UINT, ctypes.POINTER(DWORD)
)
SendMessageTimeout.restype = LRESULT


def unicode_as_lparam(source):
	pointer = ctypes.cast(ctypes.c_wchar_p(source), ctypes.c_void_p)
	return LPARAM(pointer.value)
