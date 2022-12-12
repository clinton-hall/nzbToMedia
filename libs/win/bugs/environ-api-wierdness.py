import ctypes
from jaraco.windows import environ
import os

getenv = ctypes.cdll.msvcrt.getenv
getenv.restype = ctypes.c_char_p
putenv = ctypes.cdll.msvcrt._putenv


def do_putenv(*pair):
    return putenv("=".join(pair))


def print_environment_variable(key):
    for method in (os.environ.get, os.getenv, environ.GetEnvironmentVariable, getenv):
        try:
            print(repr(method(key)))
        except Exception as e:
            print(e, end=' ')
    print


def do_test():
    key = 'TEST_PYTHON_ENVIRONMENT'
    print_environment_variable(key)
    methods = (
        os.environ.__setitem__,
        os.putenv,
        environ.SetEnvironmentVariable,
        do_putenv,
    )
    for i, method in enumerate(methods):
        print('round', i)
        method(key, 'value when using method %d' % i)
        print_environment_variable(key)


if __name__ == '__main__':
    do_test()
