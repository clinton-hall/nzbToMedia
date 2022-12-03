"""
Python routines to interface with the Microsoft
Data Protection API (DPAPI).

>>> orig_data = b'Ipsum Lorem...'
>>> ciphertext = CryptProtectData(orig_data)
>>> descr, data = CryptUnprotectData(ciphertext)
>>> data == orig_data
True
"""

import ctypes
from ctypes import wintypes
from jaraco.windows.error import handle_nonzero_success


# for type declarations
__import__('jaraco.windows.api.memory')


class DATA_BLOB(ctypes.Structure):
    r"""
    A data blob structure for use with MS DPAPI functions.

    Initialize with string of characters
    >>> input = b'abc123\x00456'
    >>> blob = DATA_BLOB(input)
    >>> len(blob)
    10
    >>> blob.get_data() == input
    True
    """
    _fields_ = [('data_size', wintypes.DWORD), ('data', ctypes.c_void_p)]

    def __init__(self, data=None):
        super(DATA_BLOB, self).__init__()
        self.set_data(data)

    def set_data(self, data):
        "Use this method to set the data for this blob"
        if data is None:
            self.data_size = 0
            self.data = None
            return
        self.data_size = len(data)
        # create a string buffer so that null bytes aren't interpreted
        #  as the end of the string
        self.data = ctypes.cast(ctypes.create_string_buffer(data), ctypes.c_void_p)

    def get_data(self):
        "Get the data for this blob"
        array = ctypes.POINTER(ctypes.c_char * len(self))
        return ctypes.cast(self.data, array).contents.raw

    def __len__(self):
        return self.data_size

    def __str__(self):
        return self.get_data()

    def free(self):
        """
        "data out" blobs have locally-allocated memory.
        Call this method to free the memory allocated by CryptProtectData
        and CryptUnprotectData.
        """
        ctypes.windll.kernel32.LocalFree(self.data)


p_DATA_BLOB = ctypes.POINTER(DATA_BLOB)

_CryptProtectData = ctypes.windll.crypt32.CryptProtectData
_CryptProtectData.argtypes = [
    p_DATA_BLOB,  # data in
    wintypes.LPCWSTR,  # data description
    p_DATA_BLOB,  # optional entropy
    ctypes.c_void_p,  # reserved
    ctypes.c_void_p,  # POINTER(CRYPTPROTECT_PROMPTSTRUCT), # prompt struct
    wintypes.DWORD,  # flags
    p_DATA_BLOB,  # data out
]
_CryptProtectData.restype = wintypes.BOOL

_CryptUnprotectData = ctypes.windll.crypt32.CryptUnprotectData
_CryptUnprotectData.argtypes = [
    p_DATA_BLOB,  # data in
    ctypes.POINTER(wintypes.LPWSTR),  # data description
    p_DATA_BLOB,  # optional entropy
    ctypes.c_void_p,  # reserved
    ctypes.c_void_p,  # POINTER(CRYPTPROTECT_PROMPTSTRUCT), # prompt struct
    wintypes.DWORD,  # flags
    p_DATA_BLOB,  # data out
]
_CryptUnprotectData.restype = wintypes.BOOL

CRYPTPROTECT_UI_FORBIDDEN = 0x01


def CryptProtectData(
    data, description=None, optional_entropy=None, prompt_struct=None, flags=0
):
    """
    Encrypt data
    """
    data_in = DATA_BLOB(data)
    entropy = DATA_BLOB(optional_entropy) if optional_entropy else None
    data_out = DATA_BLOB()

    res = _CryptProtectData(
        data_in, description, entropy, None, prompt_struct, flags, data_out  # reserved
    )
    handle_nonzero_success(res)
    res = data_out.get_data()
    data_out.free()
    return res


def CryptUnprotectData(data, optional_entropy=None, prompt_struct=None, flags=0):
    """
    Returns a tuple of (description, data) where description is the
    the description that was passed to the CryptProtectData call and
    data is the decrypted result.
    """
    data_in = DATA_BLOB(data)
    entropy = DATA_BLOB(optional_entropy) if optional_entropy else None
    data_out = DATA_BLOB()
    ptr_description = wintypes.LPWSTR()
    res = _CryptUnprotectData(
        data_in,
        ctypes.byref(ptr_description),
        entropy,
        None,  # reserved
        prompt_struct,
        flags | CRYPTPROTECT_UI_FORBIDDEN,
        data_out,
    )
    handle_nonzero_success(res)
    description = ptr_description.value
    if ptr_description.value is not None:
        ctypes.windll.kernel32.LocalFree(ptr_description)
    res = data_out.get_data()
    data_out.free()
    return description, res
