#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import operator
import collections
import functools
import stat
from ctypes import (
	POINTER, byref, cast, create_unicode_buffer,
	create_string_buffer, windll)
from ctypes.wintypes import LPWSTR
import nt
import posixpath

import six
from six.moves import builtins, filter, map

from jaraco.structures import binary

from jaraco.windows.error import WindowsError, handle_nonzero_success
import jaraco.windows.api.filesystem as api
from jaraco.windows import reparse


def mklink():
	"""
	Like cmd.exe's mklink except it will infer directory status of the
	target.
	"""
	from optparse import OptionParser
	parser = OptionParser(usage="usage: %prog [options] link target")
	parser.add_option(
		'-d', '--directory',
		help="Target is a directory (only necessary if not present)",
		action="store_true")
	options, args = parser.parse_args()
	try:
		link, target = args
	except ValueError:
		parser.error("incorrect number of arguments")
	symlink(target, link, options.directory)
	sys.stdout.write("Symbolic link created: %(link)s --> %(target)s\n" % vars())


def _is_target_a_directory(link, rel_target):
	"""
	If creating a symlink from link to a target, determine if target
	is a directory (relative to dirname(link)).
	"""
	target = os.path.join(os.path.dirname(link), rel_target)
	return os.path.isdir(target)


def symlink(target, link, target_is_directory=False):
	"""
	An implementation of os.symlink for Windows (Vista and greater)
	"""
	target_is_directory = (
		target_is_directory or
		_is_target_a_directory(link, target)
	)
	# normalize the target (MS symlinks don't respect forward slashes)
	target = os.path.normpath(target)
	handle_nonzero_success(
		api.CreateSymbolicLink(link, target, target_is_directory))


def link(target, link):
	"""
	Establishes a hard link between an existing file and a new file.
	"""
	handle_nonzero_success(api.CreateHardLink(link, target, None))


def is_reparse_point(path):
	"""
	Determine if the given path is a reparse point.
	Return False if the file does not exist or the file attributes cannot
	be determined.
	"""
	res = api.GetFileAttributes(path)
	return (
		res != api.INVALID_FILE_ATTRIBUTES
		and bool(res & api.FILE_ATTRIBUTE_REPARSE_POINT)
	)


def islink(path):
	"Determine if the given path is a symlink"
	return is_reparse_point(path) and is_symlink(path)


def _patch_path(path):
	"""
	Paths have a max length of api.MAX_PATH characters (260). If a target path
	is longer than that, it needs to be made absolute and prepended with
	\\?\ in order to work with API calls.
	See http://msdn.microsoft.com/en-us/library/aa365247%28v=vs.85%29.aspx for
	details.
	"""
	if path.startswith('\\\\?\\'):
		return path
	abs_path = os.path.abspath(path)
	if not abs_path[1] == ':':
		# python doesn't include the drive letter, but \\?\ requires it
		abs_path = os.getcwd()[:2] + abs_path
	return '\\\\?\\' + abs_path


def is_symlink(path):
	"""
	Assuming path is a reparse point, determine if it's a symlink.
	"""
	path = _patch_path(path)
	try:
		return _is_symlink(next(find_files(path)))
	except WindowsError as orig_error:
		tmpl = "Error accessing {path}: {orig_error.message}"
		raise builtins.WindowsError(tmpl.format(**locals()))


def _is_symlink(find_data):
	return find_data.reserved[0] == api.IO_REPARSE_TAG_SYMLINK


def find_files(spec):
	"""
	A pythonic wrapper around the FindFirstFile/FindNextFile win32 api.

	>>> root_files = tuple(find_files(r'c:\*'))
	>>> len(root_files) > 1
	True
	>>> root_files[0].filename == root_files[1].filename
	False

	This test might fail on a non-standard installation
	>>> 'Windows' in (fd.filename for fd in root_files)
	True
	"""
	fd = api.WIN32_FIND_DATA()
	handle = api.FindFirstFile(spec, byref(fd))
	while True:
		if handle == api.INVALID_HANDLE_VALUE:
			raise WindowsError()
		yield fd
		fd = api.WIN32_FIND_DATA()
		res = api.FindNextFile(handle, byref(fd))
		if res == 0:  # error
			error = WindowsError()
			if error.code == api.ERROR_NO_MORE_FILES:
				break
			else:
				raise error
	# todo: how to close handle when generator is destroyed?
	# hint: catch GeneratorExit
	windll.kernel32.FindClose(handle)


def get_final_path(path):
	"""
	For a given path, determine the ultimate location of that path.
	Useful for resolving symlink targets.
	This functions wraps the GetFinalPathNameByHandle from the Windows
	SDK.

	Note, this function fails if a handle cannot be obtained (such as
	for C:\Pagefile.sys on a stock windows system). Consider using
	trace_symlink_target instead.
	"""
	desired_access = api.NULL
	share_mode = (
		api.FILE_SHARE_READ | api.FILE_SHARE_WRITE | api.FILE_SHARE_DELETE
	)
	security_attributes = api.LPSECURITY_ATTRIBUTES()  # NULL pointer
	hFile = api.CreateFile(
		path,
		desired_access,
		share_mode,
		security_attributes,
		api.OPEN_EXISTING,
		api.FILE_FLAG_BACKUP_SEMANTICS,
		api.NULL,
	)

	if hFile == api.INVALID_HANDLE_VALUE:
		raise WindowsError()

	buf_size = api.GetFinalPathNameByHandle(
		hFile, LPWSTR(), 0, api.VOLUME_NAME_DOS)
	handle_nonzero_success(buf_size)
	buf = create_unicode_buffer(buf_size)
	result_length = api.GetFinalPathNameByHandle(
		hFile, buf, len(buf), api.VOLUME_NAME_DOS)

	assert result_length < len(buf)
	handle_nonzero_success(result_length)
	handle_nonzero_success(api.CloseHandle(hFile))

	return buf[:result_length]


def compat_stat(path):
	"""
	Generate stat as found on Python 3.2 and later.
	"""
	stat = os.stat(path)
	info = get_file_info(path)
	# rewrite st_ino, st_dev, and st_nlink based on file info
	return nt.stat_result(
		(stat.st_mode,) +
		(info.file_index, info.volume_serial_number, info.number_of_links) +
		stat[4:]
	)


def samefile(f1, f2):
	"""
	Backport of samefile from Python 3.2 with support for Windows.
	"""
	return posixpath.samestat(compat_stat(f1), compat_stat(f2))


def get_file_info(path):
	# open the file the same way CPython does in posixmodule.c
	desired_access = api.FILE_READ_ATTRIBUTES
	share_mode = 0
	security_attributes = None
	creation_disposition = api.OPEN_EXISTING
	flags_and_attributes = (
		api.FILE_ATTRIBUTE_NORMAL |
		api.FILE_FLAG_BACKUP_SEMANTICS |
		api.FILE_FLAG_OPEN_REPARSE_POINT
	)
	template_file = None

	handle = api.CreateFile(
		path,
		desired_access,
		share_mode,
		security_attributes,
		creation_disposition,
		flags_and_attributes,
		template_file,
	)

	if handle == api.INVALID_HANDLE_VALUE:
		raise WindowsError()

	info = api.BY_HANDLE_FILE_INFORMATION()
	res = api.GetFileInformationByHandle(handle, info)
	handle_nonzero_success(res)
	handle_nonzero_success(api.CloseHandle(handle))

	return info


def GetBinaryType(filepath):
	res = api.DWORD()
	handle_nonzero_success(api._GetBinaryType(filepath, res))
	return res


def _make_null_terminated_list(obs):
	obs = _makelist(obs)
	if obs is None:
		return
	return u'\x00'.join(obs) + u'\x00\x00'


def _makelist(ob):
	if ob is None:
		return
	if not isinstance(ob, (list, tuple, set)):
		return [ob]
	return ob


def SHFileOperation(operation, from_, to=None, flags=[]):
	flags = functools.reduce(operator.or_, flags, 0)
	from_ = _make_null_terminated_list(from_)
	to = _make_null_terminated_list(to)
	params = api.SHFILEOPSTRUCT(0, operation, from_, to, flags)
	res = api._SHFileOperation(params)
	if res != 0:
		raise RuntimeError("SHFileOperation returned %d" % res)


def join(*paths):
	r"""
	Wrapper around os.path.join that works with Windows drive letters.

	>>> join('d:\\foo', '\\bar')
	'd:\\bar'
	"""
	paths_with_drives = map(os.path.splitdrive, paths)
	drives, paths = zip(*paths_with_drives)
	# the drive we care about is the last one in the list
	drive = next(filter(None, reversed(drives)), '')
	return os.path.join(drive, os.path.join(*paths))


def resolve_path(target, start=os.path.curdir):
	r"""
	Find a path from start to target where target is relative to start.

	>>> tmp = str(getfixture('tmpdir_as_cwd'))

	>>> findpath('d:\\')
	'd:\\'

	>>> findpath('d:\\', tmp)
	'd:\\'

	>>> findpath('\\bar', 'd:\\')
	'd:\\bar'

	>>> findpath('\\bar', 'd:\\foo') # fails with '\\bar'
	'd:\\bar'

	>>> findpath('bar', 'd:\\foo')
	'd:\\foo\\bar'

	>>> findpath('\\baz', 'd:\\foo\\bar') # fails with '\\baz'
	'd:\\baz'

	>>> os.path.abspath(findpath('\\bar')).lower()
	'c:\\bar'

	>>> os.path.abspath(findpath('bar'))
	'...\\bar'

	>>> findpath('..', 'd:\\foo\\bar')
	'd:\\foo'

	The parent of the root directory is the root directory.
	>>> findpath('..', 'd:\\')
	'd:\\'
	"""
	return os.path.normpath(join(start, target))


findpath = resolve_path


def trace_symlink_target(link):
	"""
	Given a file that is known to be a symlink, trace it to its ultimate
	target.

	Raises TargetNotPresent when the target cannot be determined.
	Raises ValueError when the specified link is not a symlink.
	"""

	if not is_symlink(link):
		raise ValueError("link must point to a symlink on the system")
	while is_symlink(link):
		orig = os.path.dirname(link)
		link = readlink(link)
		link = resolve_path(link, orig)
	return link


def readlink(link):
	"""
	readlink(link) -> target
	Return a string representing the path to which the symbolic link points.
	"""
	handle = api.CreateFile(
		link,
		0,
		0,
		None,
		api.OPEN_EXISTING,
		api.FILE_FLAG_OPEN_REPARSE_POINT | api.FILE_FLAG_BACKUP_SEMANTICS,
		None,
	)

	if handle == api.INVALID_HANDLE_VALUE:
		raise WindowsError()

	res = reparse.DeviceIoControl(
		handle, api.FSCTL_GET_REPARSE_POINT, None, 10240)

	bytes = create_string_buffer(res)
	p_rdb = cast(bytes, POINTER(api.REPARSE_DATA_BUFFER))
	rdb = p_rdb.contents
	if not rdb.tag == api.IO_REPARSE_TAG_SYMLINK:
		raise RuntimeError("Expected IO_REPARSE_TAG_SYMLINK, but got %d" % rdb.tag)

	handle_nonzero_success(api.CloseHandle(handle))
	return rdb.get_substitute_name()


def patch_os_module():
	"""
	jaraco.windows provides the os.symlink and os.readlink functions.
	Monkey-patch the os module to include them if not present.
	"""
	if not hasattr(os, 'symlink'):
		os.symlink = symlink
		os.path.islink = islink
	if not hasattr(os, 'readlink'):
		os.readlink = readlink


def find_symlinks(root):
	for dirpath, dirnames, filenames in os.walk(root):
		for name in dirnames + filenames:
			pathname = os.path.join(dirpath, name)
			if is_symlink(pathname):
				yield pathname
				# don't traverse symlinks
				if name in dirnames:
					dirnames.remove(name)


def find_symlinks_cmd():
	"""
	%prog [start-path]
	Search the specified path (defaults to the current directory) for symlinks,
	printing the source and target on each line.
	"""
	from optparse import OptionParser
	from textwrap import dedent
	parser = OptionParser(usage=dedent(find_symlinks_cmd.__doc__).strip())
	options, args = parser.parse_args()
	if not args:
		args = ['.']
	root = args.pop()
	if args:
		parser.error("unexpected argument(s)")
	try:
		for symlink in find_symlinks(root):
			target = readlink(symlink)
			dir = ['', 'D'][os.path.isdir(symlink)]
			msg = '{dir:2}{symlink} --> {target}'.format(**locals())
			print(msg)
	except KeyboardInterrupt:
		pass


@six.add_metaclass(binary.BitMask)
class FileAttributes(int):

	# extract the values from the stat module on Python 3.5
	# and later.
	locals().update(
		(name.split('FILE_ATTRIBUTES_')[1].lower(), value)
		for name, value in vars(stat).items()
		if name.startswith('FILE_ATTRIBUTES_')
	)

	# For Python 3.4 and earlier, define the constants here
	archive = 0x20
	compressed = 0x800
	hidden = 0x2
	device = 0x40
	directory = 0x10
	encrypted = 0x4000
	normal = 0x80
	not_content_indexed = 0x2000
	offline = 0x1000
	read_only = 0x1
	reparse_point = 0x400
	sparse_file = 0x200
	system = 0x4
	temporary = 0x100
	virtual = 0x10000

	@classmethod
	def get(cls, filepath):
		attrs = api.GetFileAttributes(filepath)
		if attrs == api.INVALID_FILE_ATTRIBUTES:
			raise WindowsError()
		return cls(attrs)


GetFileAttributes = FileAttributes.get


def SetFileAttributes(filepath, *attrs):
	"""
	Set file attributes. e.g.:

		SetFileAttributes('C:\\foo', 'hidden')

	Each attr must be either a numeric value, a constant defined in
	jaraco.windows.filesystem.api, or one of the nice names
	defined in this function.
	"""
	nice_names = collections.defaultdict(
		lambda key: key,
		hidden='FILE_ATTRIBUTE_HIDDEN',
		read_only='FILE_ATTRIBUTE_READONLY',
	)
	flags = (getattr(api, nice_names[attr], attr) for attr in attrs)
	flags = functools.reduce(operator.or_, flags)
	handle_nonzero_success(api.SetFileAttributes(filepath, flags))
