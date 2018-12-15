import ctypes.wintypes

# MPR - Multiple Provider Router
mpr = ctypes.windll.mpr

RESOURCETYPE_ANY = 0


class NETRESOURCE(ctypes.Structure):
	_fields_ = [
		('scope', ctypes.wintypes.DWORD),
		('type', ctypes.wintypes.DWORD),
		('display_type', ctypes.wintypes.DWORD),
		('usage', ctypes.wintypes.DWORD),
		('local_name', ctypes.wintypes.LPWSTR),
		('remote_name', ctypes.wintypes.LPWSTR),
		('comment', ctypes.wintypes.LPWSTR),
		('provider', ctypes.wintypes.LPWSTR),
	]


LPNETRESOURCE = ctypes.POINTER(NETRESOURCE)

WNetAddConnection2 = mpr.WNetAddConnection2W
WNetAddConnection2.argtypes = (
	LPNETRESOURCE,
	ctypes.wintypes.LPCWSTR,
	ctypes.wintypes.LPCWSTR,
	ctypes.wintypes.DWORD,
)
