from __future__ import print_function

import ctypes
from ctypes import wintypes

from .api import security
from .api import privilege
from .api import process


def get_process_token():
	"""
	Get the current process token
	"""
	token = wintypes.HANDLE()
	res = process.OpenProcessToken(
		process.GetCurrentProcess(), process.TOKEN_ALL_ACCESS, token)
	if not res > 0:
		raise RuntimeError("Couldn't get process token")
	return token


def get_symlink_luid():
	"""
	Get the LUID for the SeCreateSymbolicLinkPrivilege
	"""
	symlink_luid = privilege.LUID()
	res = privilege.LookupPrivilegeValue(
		None, "SeCreateSymbolicLinkPrivilege", symlink_luid)
	if not res > 0:
		raise RuntimeError("Couldn't lookup privilege value")
	return symlink_luid


def get_privilege_information():
	"""
	Get all privileges associated with the current process.
	"""
	# first call with zero length to determine what size buffer we need

	return_length = wintypes.DWORD()
	params = [
		get_process_token(),
		privilege.TOKEN_INFORMATION_CLASS.TokenPrivileges,
		None,
		0,
		return_length,
	]

	res = privilege.GetTokenInformation(*params)

	# assume we now have the necessary length in return_length

	buffer = ctypes.create_string_buffer(return_length.value)
	params[2] = buffer
	params[3] = return_length.value

	res = privilege.GetTokenInformation(*params)
	assert res > 0, "Error in second GetTokenInformation (%d)" % res

	privileges = ctypes.cast(
		buffer, ctypes.POINTER(privilege.TOKEN_PRIVILEGES)).contents
	return privileges


def report_privilege_information():
	"""
	Report all privilege information assigned to the current process.
	"""
	privileges = get_privilege_information()
	print("found {0} privileges".format(privileges.count))
	tuple(map(print, privileges))


def enable_symlink_privilege():
	"""
	Try to assign the symlink privilege to the current process token.
	Return True if the assignment is successful.
	"""
	# create a space in memory for a TOKEN_PRIVILEGES structure
	#  with one element
	size = ctypes.sizeof(privilege.TOKEN_PRIVILEGES)
	size += ctypes.sizeof(privilege.LUID_AND_ATTRIBUTES)
	buffer = ctypes.create_string_buffer(size)
	tp = ctypes.cast(buffer, ctypes.POINTER(privilege.TOKEN_PRIVILEGES)).contents
	tp.count = 1
	tp.get_array()[0].enable()
	tp.get_array()[0].LUID = get_symlink_luid()
	token = get_process_token()
	res = privilege.AdjustTokenPrivileges(token, False, tp, 0, None, None)
	if res == 0:
		raise RuntimeError("Error in AdjustTokenPrivileges")

	ERROR_NOT_ALL_ASSIGNED = 1300
	return ctypes.windll.kernel32.GetLastError() != ERROR_NOT_ALL_ASSIGNED


class PolicyHandle(wintypes.HANDLE):
	pass


class LSA_UNICODE_STRING(ctypes.Structure):
	_fields_ = [
		('length', ctypes.c_ushort),
		('max_length', ctypes.c_ushort),
		('buffer', ctypes.wintypes.LPWSTR),
	]


def OpenPolicy(system_name, object_attributes, access_mask):
	policy = PolicyHandle()
	raise NotImplementedError(
		"Need to construct structures for parameters "
		"(see http://msdn.microsoft.com/en-us/library/windows"
		"/desktop/aa378299%28v=vs.85%29.aspx)")
	res = ctypes.windll.advapi32.LsaOpenPolicy(
		system_name, object_attributes,
		access_mask, ctypes.byref(policy))
	assert res == 0, "Error status {res}".format(**vars())
	return policy


def grant_symlink_privilege(who, machine=''):
	"""
	Grant the 'create symlink' privilege to who.

	Based on http://support.microsoft.com/kb/132958
	"""
	flags = security.POLICY_CREATE_ACCOUNT | security.POLICY_LOOKUP_NAMES
	policy = OpenPolicy(machine, flags)
	return policy


def main():
	assigned = enable_symlink_privilege()
	msg = ['failure', 'success'][assigned]

	print("Symlink privilege assignment completed with {0}".format(msg))


if __name__ == '__main__':
	main()
