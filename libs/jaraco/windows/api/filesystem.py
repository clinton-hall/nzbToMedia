import ctypes.wintypes

CreateSymbolicLink = ctypes.windll.kernel32.CreateSymbolicLinkW
CreateSymbolicLink.argtypes = (
	ctypes.wintypes.LPWSTR,
	ctypes.wintypes.LPWSTR,
	ctypes.wintypes.DWORD,
)
CreateSymbolicLink.restype = ctypes.wintypes.BOOLEAN

CreateHardLink = ctypes.windll.kernel32.CreateHardLinkW
CreateHardLink.argtypes = (
	ctypes.wintypes.LPWSTR,
	ctypes.wintypes.LPWSTR,
	ctypes.wintypes.LPVOID,  # reserved for LPSECURITY_ATTRIBUTES
)
CreateHardLink.restype = ctypes.wintypes.BOOLEAN

GetFileAttributes = ctypes.windll.kernel32.GetFileAttributesW
GetFileAttributes.argtypes = ctypes.wintypes.LPWSTR,
GetFileAttributes.restype = ctypes.wintypes.DWORD

SetFileAttributes = ctypes.windll.kernel32.SetFileAttributesW
SetFileAttributes.argtypes = ctypes.wintypes.LPWSTR, ctypes.wintypes.DWORD
SetFileAttributes.restype = ctypes.wintypes.BOOL

MAX_PATH = 260

GetFinalPathNameByHandle = ctypes.windll.kernel32.GetFinalPathNameByHandleW
GetFinalPathNameByHandle.argtypes = (
	ctypes.wintypes.HANDLE, ctypes.wintypes.LPWSTR, ctypes.wintypes.DWORD,
	ctypes.wintypes.DWORD,
)
GetFinalPathNameByHandle.restype = ctypes.wintypes.DWORD


class SECURITY_ATTRIBUTES(ctypes.Structure):
	_fields_ = (
		('length', ctypes.wintypes.DWORD),
		('p_security_descriptor', ctypes.wintypes.LPVOID),
		('inherit_handle', ctypes.wintypes.BOOLEAN),
	)


LPSECURITY_ATTRIBUTES = ctypes.POINTER(SECURITY_ATTRIBUTES)

CreateFile = ctypes.windll.kernel32.CreateFileW
CreateFile.argtypes = (
	ctypes.wintypes.LPWSTR,
	ctypes.wintypes.DWORD,
	ctypes.wintypes.DWORD,
	LPSECURITY_ATTRIBUTES,
	ctypes.wintypes.DWORD,
	ctypes.wintypes.DWORD,
	ctypes.wintypes.HANDLE,
)
CreateFile.restype = ctypes.wintypes.HANDLE
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x2000000
NULL = 0
OPEN_EXISTING = 3
FILE_ATTRIBUTE_READONLY = 0x1
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_DIRECTORY = 0x10
FILE_ATTRIBUTE_NORMAL = 0x80
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
GENERIC_READ = 0x80000000
FILE_READ_ATTRIBUTES = 0x80
INVALID_HANDLE_VALUE = ctypes.wintypes.HANDLE(-1).value

INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF

ERROR_NO_MORE_FILES = 0x12

VOLUME_NAME_DOS = 0

CloseHandle = ctypes.windll.kernel32.CloseHandle
CloseHandle.argtypes = (ctypes.wintypes.HANDLE,)
CloseHandle.restype = ctypes.wintypes.BOOLEAN


class WIN32_FIND_DATA(ctypes.wintypes.WIN32_FIND_DATAW):
	"""
	_fields_ = [
		("dwFileAttributes", DWORD),
		("ftCreationTime", FILETIME),
		("ftLastAccessTime", FILETIME),
		("ftLastWriteTime", FILETIME),
		("nFileSizeHigh", DWORD),
		("nFileSizeLow", DWORD),
		("dwReserved0", DWORD),
		("dwReserved1", DWORD),
		("cFileName", WCHAR * MAX_PATH),
		("cAlternateFileName", WCHAR * 14)]
	]
	"""

	@property
	def file_attributes(self):
		return self.dwFileAttributes

	@property
	def creation_time(self):
		return self.ftCreationTime

	@property
	def last_access_time(self):
		return self.ftLastAccessTime

	@property
	def last_write_time(self):
		return self.ftLastWriteTime

	@property
	def file_size_words(self):
		return [self.nFileSizeHigh, self.nFileSizeLow]

	@property
	def reserved(self):
		return [self.dwReserved0, self.dwReserved1]

	@property
	def filename(self):
		return self.cFileName

	@property
	def alternate_filename(self):
		return self.cAlternateFileName

	@property
	def file_size(self):
		return self.nFileSizeHigh << 32 + self.nFileSizeLow


LPWIN32_FIND_DATA = ctypes.POINTER(ctypes.wintypes.WIN32_FIND_DATAW)

FindFirstFile = ctypes.windll.kernel32.FindFirstFileW
FindFirstFile.argtypes = (ctypes.wintypes.LPWSTR, LPWIN32_FIND_DATA)
FindFirstFile.restype = ctypes.wintypes.HANDLE
FindNextFile = ctypes.windll.kernel32.FindNextFileW
FindNextFile.argtypes = (ctypes.wintypes.HANDLE, LPWIN32_FIND_DATA)
FindNextFile.restype = ctypes.wintypes.BOOLEAN

ctypes.windll.kernel32.FindClose.argtypes = ctypes.wintypes.HANDLE,

SCS_32BIT_BINARY = 0  # A 32-bit Windows-based application
SCS_64BIT_BINARY = 6  # A 64-bit Windows-based application
SCS_DOS_BINARY = 1  # An MS-DOS-based application
SCS_OS216_BINARY = 5  # A 16-bit OS/2-based application
SCS_PIF_BINARY = 3  # A PIF file that executes an MS-DOS-based application
SCS_POSIX_BINARY = 4  # A POSIX-based application
SCS_WOW_BINARY = 2  # A 16-bit Windows-based application

_GetBinaryType = ctypes.windll.kernel32.GetBinaryTypeW
_GetBinaryType.argtypes = (
	ctypes.wintypes.LPWSTR, ctypes.POINTER(ctypes.wintypes.DWORD),
)
_GetBinaryType.restype = ctypes.wintypes.BOOL

FILEOP_FLAGS = ctypes.wintypes.WORD


class BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
	_fields_ = [
		('file_attributes', ctypes.wintypes.DWORD),
		('creation_time', ctypes.wintypes.FILETIME),
		('last_access_time', ctypes.wintypes.FILETIME),
		('last_write_time', ctypes.wintypes.FILETIME),
		('volume_serial_number', ctypes.wintypes.DWORD),
		('file_size_high', ctypes.wintypes.DWORD),
		('file_size_low', ctypes.wintypes.DWORD),
		('number_of_links', ctypes.wintypes.DWORD),
		('file_index_high', ctypes.wintypes.DWORD),
		('file_index_low', ctypes.wintypes.DWORD),
	]

	@property
	def file_size(self):
		return (self.file_size_high << 32) + self.file_size_low

	@property
	def file_index(self):
		return (self.file_index_high << 32) + self.file_index_low


GetFileInformationByHandle = ctypes.windll.kernel32.GetFileInformationByHandle
GetFileInformationByHandle.restype = ctypes.wintypes.BOOL
GetFileInformationByHandle.argtypes = (
	ctypes.wintypes.HANDLE,
	ctypes.POINTER(BY_HANDLE_FILE_INFORMATION),
)


class SHFILEOPSTRUCT(ctypes.Structure):
	_fields_ = [
		('status_dialog', ctypes.wintypes.HWND),
		('operation', ctypes.wintypes.UINT),
		('from_', ctypes.wintypes.LPWSTR),
		('to', ctypes.wintypes.LPWSTR),
		('flags', FILEOP_FLAGS),
		('operations_aborted', ctypes.wintypes.BOOL),
		('name_mapping_handles', ctypes.wintypes.LPVOID),
		('progress_title', ctypes.wintypes.LPWSTR),
	]


_SHFileOperation = ctypes.windll.shell32.SHFileOperationW
_SHFileOperation.argtypes = [ctypes.POINTER(SHFILEOPSTRUCT)]
_SHFileOperation.restype = ctypes.c_int

FOF_ALLOWUNDO = 64
FOF_NOCONFIRMATION = 16
FO_DELETE = 3

ReplaceFile = ctypes.windll.kernel32.ReplaceFileW
ReplaceFile.restype = ctypes.wintypes.BOOL
ReplaceFile.argtypes = [
	ctypes.wintypes.LPWSTR,
	ctypes.wintypes.LPWSTR,
	ctypes.wintypes.LPWSTR,
	ctypes.wintypes.DWORD,
	ctypes.wintypes.LPVOID,
	ctypes.wintypes.LPVOID,
]

REPLACEFILE_WRITE_THROUGH = 0x1
REPLACEFILE_IGNORE_MERGE_ERRORS = 0x2
REPLACEFILE_IGNORE_ACL_ERRORS = 0x4


class STAT_STRUCT(ctypes.Structure):
	_fields_ = [
		('dev', ctypes.c_uint),
		('ino', ctypes.c_ushort),
		('mode', ctypes.c_ushort),
		('nlink', ctypes.c_short),
		('uid', ctypes.c_short),
		('gid', ctypes.c_short),
		('rdev', ctypes.c_uint),
		# the following 4 fields are ctypes.c_uint64 for _stat64
		('size', ctypes.c_uint),
		('atime', ctypes.c_uint),
		('mtime', ctypes.c_uint),
		('ctime', ctypes.c_uint),
	]


_wstat = ctypes.windll.msvcrt._wstat
_wstat.argtypes = [ctypes.wintypes.LPWSTR, ctypes.POINTER(STAT_STRUCT)]
_wstat.restype = ctypes.c_int

FILE_NOTIFY_CHANGE_LAST_WRITE = 0x10

FindFirstChangeNotification = (
	ctypes.windll.kernel32.FindFirstChangeNotificationW)
FindFirstChangeNotification.argtypes = (
	ctypes.wintypes.LPWSTR, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD,
)
FindFirstChangeNotification.restype = ctypes.wintypes.HANDLE

FindCloseChangeNotification = (
	ctypes.windll.kernel32.FindCloseChangeNotification)
FindCloseChangeNotification.argtypes = ctypes.wintypes.HANDLE,
FindCloseChangeNotification.restype = ctypes.wintypes.BOOL

FindNextChangeNotification = ctypes.windll.kernel32.FindNextChangeNotification
FindNextChangeNotification.argtypes = ctypes.wintypes.HANDLE,
FindNextChangeNotification.restype = ctypes.wintypes.BOOL

FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
IO_REPARSE_TAG_SYMLINK = 0xA000000C
FSCTL_GET_REPARSE_POINT = 0x900a8

LPDWORD = ctypes.POINTER(ctypes.wintypes.DWORD)
LPOVERLAPPED = ctypes.wintypes.LPVOID

DeviceIoControl = ctypes.windll.kernel32.DeviceIoControl
DeviceIoControl.argtypes = [
	ctypes.wintypes.HANDLE,
	ctypes.wintypes.DWORD,
	ctypes.wintypes.LPVOID,
	ctypes.wintypes.DWORD,
	ctypes.wintypes.LPVOID,
	ctypes.wintypes.DWORD,
	LPDWORD,
	LPOVERLAPPED,
]
DeviceIoControl.restype = ctypes.wintypes.BOOL


class REPARSE_DATA_BUFFER(ctypes.Structure):
	_fields_ = [
		('tag', ctypes.c_ulong),
		('data_length', ctypes.c_ushort),
		('reserved', ctypes.c_ushort),
		('substitute_name_offset', ctypes.c_ushort),
		('substitute_name_length', ctypes.c_ushort),
		('print_name_offset', ctypes.c_ushort),
		('print_name_length', ctypes.c_ushort),
		('flags', ctypes.c_ulong),
		('path_buffer', ctypes.c_byte * 1),
	]

	def get_print_name(self):
		wchar_size = ctypes.sizeof(ctypes.wintypes.WCHAR)
		arr_typ = ctypes.wintypes.WCHAR * (self.print_name_length // wchar_size)
		data = ctypes.byref(self.path_buffer, self.print_name_offset)
		return ctypes.cast(data, ctypes.POINTER(arr_typ)).contents.value

	def get_substitute_name(self):
		wchar_size = ctypes.sizeof(ctypes.wintypes.WCHAR)
		arr_typ = ctypes.wintypes.WCHAR * (self.substitute_name_length // wchar_size)
		data = ctypes.byref(self.path_buffer, self.substitute_name_offset)
		return ctypes.cast(data, ctypes.POINTER(arr_typ)).contents.value
