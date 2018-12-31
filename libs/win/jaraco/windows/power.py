# -*- coding: utf-8 -*-

from __future__ import print_function

import itertools
import contextlib

from more_itertools.recipes import consume, unique_justseen
try:
	import wmi as wmilib
except ImportError:
	pass

from jaraco.windows.error import handle_nonzero_success
from .api import power


def GetSystemPowerStatus():
	stat = power.SYSTEM_POWER_STATUS()
	handle_nonzero_success(GetSystemPowerStatus(stat))
	return stat


def _init_power_watcher():
	global power_watcher
	if 'power_watcher' not in globals():
		wmi = wmilib.WMI()
		query = 'SELECT * from Win32_PowerManagementEvent'
		power_watcher = wmi.ExecNotificationQuery(query)


def get_power_management_events():
	_init_power_watcher()
	while True:
		yield power_watcher.NextEvent()


def wait_for_power_status_change():
	EVT_POWER_STATUS_CHANGE = 10

	def not_power_status_change(evt):
		return evt.EventType != EVT_POWER_STATUS_CHANGE
	events = get_power_management_events()
	consume(itertools.takewhile(not_power_status_change, events))


def get_unique_power_states():
	"""
	Just like get_power_states, but ensures values are returned only
	when the state changes.
	"""
	return unique_justseen(get_power_states())


def get_power_states():
	"""
	Continuously return the power state of the system when it changes.
	This function will block indefinitely if the power state never
	changes.
	"""
	while True:
		state = GetSystemPowerStatus()
		yield state.ac_line_status_string
		wait_for_power_status_change()


@contextlib.contextmanager
def no_sleep():
	"""
	Context that prevents the computer from going to sleep.
	"""
	mode = power.ES.continuous | power.ES.system_required
	handle_nonzero_success(power.SetThreadExecutionState(mode))
	try:
		yield
	finally:
		handle_nonzero_success(power.SetThreadExecutionState(power.ES.continuous))
