from ctypes import CDLL, c_char_p


def get_libc():
    libnames = ('msvcrt', 'libc.so.6')
    for libname in libnames:
        try:
            return CDLL(libname)
        except WindowsError:
            pass
        except OSError:
            pass
    raise RuntimeError("Unable to find a suitable libc (tried %s)" % libnames)


getenv = get_libc().getenv
getenv.restype = c_char_p

# call into your linked module here

print('new value is', getenv('FOO'))
