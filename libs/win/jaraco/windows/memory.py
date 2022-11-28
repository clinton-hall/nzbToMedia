import ctypes
from ctypes import WinError

from .api import memory


class LockedMemory(object):
    def __init__(self, handle):
        self.handle = handle

    def __enter__(self):
        self.data_ptr = memory.GlobalLock(self.handle)
        if not self.data_ptr:
            del self.data_ptr
            raise WinError()
        return self

    def __exit__(self, *args):
        memory.GlobalUnlock(self.handle)
        del self.data_ptr

    @property
    def data(self):
        with self:
            return ctypes.string_at(self.data_ptr, self.size)

    @property
    def size(self):
        return memory.GlobalSize(self.data_ptr)
