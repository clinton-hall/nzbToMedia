import os
import sys

try:
    from jaraco.windows.filesystem import symlink
except ImportError:
    # a dirty reimplementation of symlink from jaraco.windows
    from ctypes import windll
    from ctypes.wintypes import LPWSTR, DWORD, BOOLEAN

    CreateSymbolicLink = windll.kernel32.CreateSymbolicLinkW
    CreateSymbolicLink.argtypes = (LPWSTR, LPWSTR, DWORD)
    CreateSymbolicLink.restype = BOOLEAN

    def symlink(link, target, target_is_directory=False):
        """
        An implementation of os.symlink for Windows (Vista and greater)
        """
        target_is_directory = target_is_directory or os.path.isdir(target)
        CreateSymbolicLink(link, target, target_is_directory)


assert sys.platform in ('win32',)
os.makedirs(r'.\foo')
assert os.path.isdir(r'.\foo')

symlink(r'.\foo_sym', r'.\foo')
assert os.path.isdir(r'.\foo_sym')
assert os.path.islink(r'.\foo_sym')  # fails
