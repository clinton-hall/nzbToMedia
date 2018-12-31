#!/usr/bin/env python

import operator
import ctypes
import datetime
from ctypes.wintypes import WORD, WCHAR, BOOL, LONG

from jaraco.windows.util import Extended
from jaraco.collections import RangeMap


class AnyDict(object):
	"A dictionary that returns the same value regardless of key"

	def __init__(self, value):
		self.value = value

	def __getitem__(self, key):
		return self.value


class SYSTEMTIME(Extended, ctypes.Structure):
	_fields_ = [
		('year', WORD),
		('month', WORD),
		('day_of_week', WORD),
		('day', WORD),
		('hour', WORD),
		('minute', WORD),
		('second', WORD),
		('millisecond', WORD),
	]


class REG_TZI_FORMAT(Extended, ctypes.Structure):
	_fields_ = [
		('bias', LONG),
		('standard_bias', LONG),
		('daylight_bias', LONG),
		('standard_start', SYSTEMTIME),
		('daylight_start', SYSTEMTIME),
	]


class TIME_ZONE_INFORMATION(Extended, ctypes.Structure):
	_fields_ = [
		('bias', LONG),
		('standard_name', WCHAR * 32),
		('standard_start', SYSTEMTIME),
		('standard_bias', LONG),
		('daylight_name', WCHAR * 32),
		('daylight_start', SYSTEMTIME),
		('daylight_bias', LONG),
	]


class DYNAMIC_TIME_ZONE_INFORMATION(TIME_ZONE_INFORMATION):
	"""
	Because the structure of the DYNAMIC_TIME_ZONE_INFORMATION extends
	the structure of the TIME_ZONE_INFORMATION, this structure
	can be used as a drop-in replacement for calls where the
	structure is passed by reference.

	For example,
	dynamic_tzi = DYNAMIC_TIME_ZONE_INFORMATION()
	ctypes.windll.kernel32.GetTimeZoneInformation(ctypes.byref(dynamic_tzi))

	(although the key_name and dynamic_daylight_time_disabled flags will be
	set to the default (null)).

	>>> isinstance(DYNAMIC_TIME_ZONE_INFORMATION(), TIME_ZONE_INFORMATION)
	True


	"""
	_fields_ = [
		# ctypes automatically includes the fields from the parent
		('key_name', WCHAR * 128),
		('dynamic_daylight_time_disabled', BOOL),
	]

	def __init__(self, *args, **kwargs):
		"""Allow initialization from args from both this class and
		its superclass.  Default ctypes implementation seems to
		assume that this class is only initialized with its own
		_fields_ (for non-keyword-args)."""
		super_self = super(DYNAMIC_TIME_ZONE_INFORMATION, self)
		super_fields = super_self._fields_
		super_args = args[:len(super_fields)]
		self_args = args[len(super_fields):]
		# convert the super args to keyword args so they're also handled
		for field, arg in zip(super_fields, super_args):
			field_name, spec = field
			kwargs[field_name] = arg
		super(DYNAMIC_TIME_ZONE_INFORMATION, self).__init__(*self_args, **kwargs)


class Info(DYNAMIC_TIME_ZONE_INFORMATION):
	"""
	A time zone definition class based on the win32
	DYNAMIC_TIME_ZONE_INFORMATION structure.

	Describes a bias against UTC (bias), and two dates at which a separate
	additional bias applies (standard_bias and daylight_bias).
	"""

	def field_names(self):
		return map(operator.itemgetter(0), self._fields_)

	def __init__(self, *args, **kwargs):
		"""
		Try to construct a timezone.Info from
		a) [DYNAMIC_]TIME_ZONE_INFORMATION args
		b) another Info
		c) a REG_TZI_FORMAT
		d) a byte structure
		"""
		funcs = (
			super(Info, self).__init__,
			self.__init_from_other,
			self.__init_from_reg_tzi,
			self.__init_from_bytes,
		)
		for func in funcs:
			try:
				func(*args, **kwargs)
				return
			except TypeError:
				pass
		raise TypeError("Invalid arguments for %s" % self.__class__)

	def __init_from_bytes(self, bytes, **kwargs):
		reg_tzi = REG_TZI_FORMAT()
		# todo: use buffer API in Python 3
		buffer = memoryview(bytes)
		ctypes.memmove(ctypes.addressof(reg_tzi), buffer, len(buffer))
		self.__init_from_reg_tzi(self, reg_tzi, **kwargs)

	def __init_from_reg_tzi(self, reg_tzi, **kwargs):
		if not isinstance(reg_tzi, REG_TZI_FORMAT):
			raise TypeError("Not a REG_TZI_FORMAT")
		for field_name, type in reg_tzi._fields_:
			setattr(self, field_name, getattr(reg_tzi, field_name))
		for name, value in kwargs.items():
			setattr(self, name, value)

	def __init_from_other(self, other):
		if not isinstance(other, TIME_ZONE_INFORMATION):
			raise TypeError("Not a TIME_ZONE_INFORMATION")
		for name in other.field_names():
			# explicitly get the value from the underlying structure
			value = super(Info, other).__getattribute__(other, name)
			setattr(self, name, value)
		# consider instead of the loop above just copying the memory directly
		# size = max(ctypes.sizeof(DYNAMIC_TIME_ZONE_INFO), ctypes.sizeof(other))
		# ctypes.memmove(ctypes.addressof(self), other, size)

	def __getattribute__(self, attr):
		value = super(Info, self).__getattribute__(attr)

		def make_minute_timedelta(m):
			datetime.timedelta(minutes=m)
		if 'bias' in attr:
			value = make_minute_timedelta(value)
		return value

	@classmethod
	def current(class_):
		"Windows Platform SDK GetTimeZoneInformation"
		tzi = class_()
		kernel32 = ctypes.windll.kernel32
		getter = kernel32.GetTimeZoneInformation
		getter = getattr(kernel32, 'GetDynamicTimeZoneInformation', getter)
		code = getter(ctypes.byref(tzi))
		return code, tzi

	def set(self):
		kernel32 = ctypes.windll.kernel32
		setter = kernel32.SetTimeZoneInformation
		setter = getattr(kernel32, 'SetDynamicTimeZoneInformation', setter)
		return setter(ctypes.byref(self))

	def copy(self):
		return self.__class__(self)

	def locate_daylight_start(self, year):
		info = self.get_info_for_year(year)
		return self._locate_day(year, info.daylight_start)

	def locate_standard_start(self, year):
		info = self.get_info_for_year(year)
		return self._locate_day(year, info.standard_start)

	def get_info_for_year(self, year):
		return self.dynamic_info[year]

	@property
	def dynamic_info(self):
		"Return a map that for a given year will return the correct Info"
		if self.key_name:
			dyn_key = self.get_key().subkey('Dynamic DST')
			del dyn_key['FirstEntry']
			del dyn_key['LastEntry']
			years = map(int, dyn_key.keys())
			values = map(Info, dyn_key.values())
			# create a range mapping that searches by descending year and matches
			# if the target year is greater or equal.
			return RangeMap(zip(years, values), RangeMap.descending, operator.ge)
		else:
			return AnyDict(self)

	@staticmethod
	def _locate_day(year, cutoff):
		"""
		Takes a SYSTEMTIME object, such as retrieved from a TIME_ZONE_INFORMATION
		structure or call to GetTimeZoneInformation and interprets
		it based on the given
		year to identify the actual day.

		This method is necessary because the SYSTEMTIME structure
		refers to a day by its
		day of the week and week of the month (e.g. 4th saturday in March).

		>>> SATURDAY = 6
		>>> MARCH = 3
		>>> st = SYSTEMTIME(2000, MARCH, SATURDAY, 4, 0, 0, 0, 0)

		# according to my calendar, the 4th Saturday in March in 2009 was the 28th
		>>> expected_date = datetime.datetime(2009, 3, 28)
		>>> Info._locate_day(2009, st) == expected_date
		True
		"""
		# MS stores Sunday as 0, Python datetime stores Monday as zero
		target_weekday = (cutoff.day_of_week + 6) % 7
		# For SYSTEMTIMEs relating to time zone inforamtion, cutoff.day
		#  is the week of the month
		week_of_month = cutoff.day
		# so the following is the first day of that week
		day = (week_of_month - 1) * 7 + 1
		result = datetime.datetime(
			year, cutoff.month, day,
			cutoff.hour, cutoff.minute, cutoff.second, cutoff.millisecond)
		# now the result is the correct week, but not necessarily
		# the correct day of the week
		days_to_go = (target_weekday - result.weekday()) % 7
		result += datetime.timedelta(days_to_go)
		# if we selected a day in the month following the target month,
		#  move back a week or two.
		# This is necessary because Microsoft defines the fifth week in a month
		#  to be the last week in a month and adding the time delta might have
		#  pushed the result into the next month.
		while result.month == cutoff.month + 1:
			result -= datetime.timedelta(weeks=1)
		return result
