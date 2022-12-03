import winreg
from itertools import count


def key_values(key):
    for index in count():
        try:
            yield winreg.EnumValue(key, index)
        except WindowsError:
            break


def key_subkeys(key):
    for index in count():
        try:
            yield winreg.EnumKey(key, index)
        except WindowsError:
            break
