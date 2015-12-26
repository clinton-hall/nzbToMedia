#!/usr/bin/env python

import ctypes

def ensure_unicode(param):
	try:
		param = ctypes.create_unicode_buffer(param)
	except TypeError:
		pass # just return the param as is
	return param

class Extended(object):
	"Used to add extended capability to structures"
	def __eq__(self, other):
		return buffer(self) == buffer(other)

	def __ne__(self, other):
		return buffer(self) != buffer(other)
