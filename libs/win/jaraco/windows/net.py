"""
API hooks for network stuff.
"""

__all__ = ('AddConnection')

from jaraco.windows.error import WindowsError
from .api import net


def AddConnection(
	remote_name, type=net.RESOURCETYPE_ANY, local_name=None,
	provider_name=None, user=None, password=None, flags=0):
	resource = net.NETRESOURCE(
		type=type,
		remote_name=remote_name,
		local_name=local_name,
		provider_name=provider_name,
		# WNetAddConnection2 ignores the other members of NETRESOURCE
	)

	result = net.WNetAddConnection2(
		resource,
		password,
		user,
		flags,
	)

	if result != 0:
		raise WindowsError(result)
