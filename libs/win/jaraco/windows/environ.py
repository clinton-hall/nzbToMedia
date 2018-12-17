#!/usr/bin/env python
from __future__ import absolute_import

import sys

import ctypes
import ctypes.wintypes

import six
from six.moves import winreg

from jaraco.ui.editor import EditableFile

from jaraco.windows import error
from jaraco.windows.api import message, environ
from .registry import key_values as registry_key_values


def SetEnvironmentVariable(name, value):
	error.handle_nonzero_success(environ.SetEnvironmentVariable(name, value))


def ClearEnvironmentVariable(name):
	error.handle_nonzero_success(environ.SetEnvironmentVariable(name, None))


def GetEnvironmentVariable(name):
	max_size = 2**15 - 1
	buffer = ctypes.create_unicode_buffer(max_size)
	error.handle_nonzero_success(
		environ.GetEnvironmentVariable(name, buffer, max_size))
	return buffer.value

###


class RegisteredEnvironment(object):
	"""
	Manages the environment variables as set in the Windows Registry.
	"""

	@classmethod
	def show(class_):
		for name, value, type in registry_key_values(class_.key):
			sys.stdout.write('='.join((name, value)) + '\n')

	NoDefault = type('NoDefault', (object,), dict())

	@classmethod
	def get(class_, name, default=NoDefault):
		try:
			value, type = winreg.QueryValueEx(class_.key, name)
			return value
		except WindowsError:
			if default is not class_.NoDefault:
				return default
			raise ValueError("No such key", name)

	@classmethod
	def get_values_list(class_, name, sep):
		res = class_.get(name.upper(), [])
		if isinstance(res, six.string_types):
			res = res.split(sep)
		return res

	@classmethod
	def set(class_, name, value, options):
		# consider opening the key read-only except for here
		# key = winreg.OpenKey(class_.key, None, 0, winreg.KEY_WRITE)
		# and follow up by closing it.
		if not value:
			return class_.delete(name)
		do_append = options.append or (
			name.upper() in ('PATH', 'PATHEXT') and not options.replace
		)
		if do_append:
			sep = ';'
			values = class_.get_values_list(name, sep) + [value]
			value = sep.join(values)
		winreg.SetValueEx(class_.key, name, 0, winreg.REG_EXPAND_SZ, value)
		class_.notify()

	@classmethod
	def add(class_, name, value, sep=';'):
		"""
		Add a value to a delimited variable, but only when the value isn't
		already present.
		"""
		values = class_.get_values_list(name, sep)
		if value in values:
			return
		new_value = sep.join(values + [value])
		winreg.SetValueEx(
			class_.key, name, 0, winreg.REG_EXPAND_SZ, new_value)
		class_.notify()

	@classmethod
	def remove_values(class_, name, value_substring, options):
		sep = ';'
		values = class_.get_values_list(name, sep)
		new_values = [
			value
			for value in values
			if value_substring.lower() not in value.lower()
		]
		values = sep.join(new_values)
		winreg.SetValueEx(class_.key, name, 0, winreg.REG_EXPAND_SZ, values)
		class_.notify()

	@classmethod
	def edit(class_, name, value='', options=None):
		# value, options ignored
		sep = ';'
		values = class_.get_values_list(name, sep)
		e = EditableFile('\n'.join(values))
		e.edit()
		if e.changed:
			values = sep.join(e.data.strip().split('\n'))
			winreg.SetValueEx(class_.key, name, 0, winreg.REG_EXPAND_SZ, values)
			class_.notify()

	@classmethod
	def delete(class_, name):
		winreg.DeleteValue(class_.key, name)
		class_.notify()

	@classmethod
	def notify(class_):
		"""
		Notify other windows that the environment has changed (following
		http://support.microsoft.com/kb/104011).
		"""
		# TODO: Implement Microsoft UIPI (User Interface Privilege Isolation) to
		#  elevate privilege to system level so the system gets this notification
		# for now, this must be run as admin to work as expected
		return_val = ctypes.wintypes.DWORD()
		res = message.SendMessageTimeout(
			message.HWND_BROADCAST,
			message.WM_SETTINGCHANGE,
			0,  # wparam must be null
			'Environment',
			message.SMTO_ABORTIFHUNG,
			5000,  # timeout in ms
			return_val,
		)
		error.handle_nonzero_success(res)


class MachineRegisteredEnvironment(RegisteredEnvironment):
	path = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
	hklm = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
	try:
		key = winreg.OpenKey(
			hklm, path, 0,
			winreg.KEY_READ | winreg.KEY_WRITE)
	except WindowsError:
		key = winreg.OpenKey(hklm, path, 0, winreg.KEY_READ)


class UserRegisteredEnvironment(RegisteredEnvironment):
	hkcu = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
	key = winreg.OpenKey(
		hkcu, 'Environment', 0,
		winreg.KEY_READ | winreg.KEY_WRITE)


def trim(s):
	from textwrap import dedent
	return dedent(s).strip()


def enver(*args):
	"""
	%prog [<name>=[value]]

	To show all environment variables, call with no parameters:
		%prog
	To Add/Modify/Delete environment variable:
		%prog <name>=[value]

	If <name> is PATH or PATHEXT, %prog will by default append the value using
	a semicolon as a separator. Use -r to disable this behavior or -a to force
	it for variables other than PATH and PATHEXT.

	If append is prescribed, but the value doesn't exist, the value will be
	created.

	If there is no value, %prog will delete the <name> environment variable.
	i.e. "PATH="

	To remove a specific value or values from a semicolon-separated
	multi-value variable (such as PATH), use --remove-value.

	e.g. enver --remove-value PATH=C:\\Unwanted\\Dir\\In\\Path

	Remove-value matches case-insensitive and also matches any substring
	so the following would also be sufficient to remove the aforementioned
	undesirable dir.

	enver --remove-value PATH=UNWANTED

	Note that %prog does not affect the current running environment, and can
	only affect subsequently spawned applications.
	"""
	from optparse import OptionParser
	parser = OptionParser(usage=trim(enver.__doc__))
	parser.add_option(
		'-U', '--user-environment',
		action='store_const', const=UserRegisteredEnvironment,
		default=MachineRegisteredEnvironment,
		dest='class_',
		help="Use the current user's environment",
	)
	parser.add_option(
		'-a', '--append',
		action='store_true', default=False,
		help="Append the value to any existing value (default for PATH and PATHEXT)",
	)
	parser.add_option(
		'-r', '--replace',
		action='store_true', default=False,
		help="Replace any existing value (used to override default append "
		"for PATH and PATHEXT)",
	)
	parser.add_option(
		'--remove-value', action='store_true', default=False,
		help="Remove any matching values from a semicolon-separated "
		"multi-value variable",
	)
	parser.add_option(
		'-e', '--edit', action='store_true', default=False,
		help="Edit the value in a local editor",
	)
	options, args = parser.parse_args(*args)

	try:
		param = args.pop()
		if args:
			parser.error("Too many parameters specified")
			raise SystemExit(1)
		if '=' not in param and not options.edit:
			parser.error("Expected <name>= or <name>=<value>")
			raise SystemExit(2)
		name, sep, value = param.partition('=')
		method_name = 'set'
		if options.remove_value:
			method_name = 'remove_values'
		if options.edit:
			method_name = 'edit'
		method = getattr(options.class_, method_name)
		method(name, value, options)
	except IndexError:
		options.class_.show()


if __name__ == '__main__':
	enver()
