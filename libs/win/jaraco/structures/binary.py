import numbers
from functools import reduce


def get_bit_values(number, size=32):
    """
    Get bit values as a list for a given number

    >>> get_bit_values(1) == [0]*31 + [1]
    True

    >>> get_bit_values(0xDEADBEEF)
    [1, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, \
1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1]

    You may override the default word size of 32-bits to match your actual
    application.

    >>> get_bit_values(0x3, 2)
    [1, 1]

    >>> get_bit_values(0x3, 4)
    [0, 0, 1, 1]
    """
    number += 2 ** size
    return list(map(int, bin(number)[-size:]))


def gen_bit_values(number):
    """
    Return a zero or one for each bit of a numeric value up to the most
    significant 1 bit, beginning with the least significant bit.

    >>> list(gen_bit_values(16))
    [0, 0, 0, 0, 1]
    """
    digits = bin(number)[2:]
    return map(int, reversed(digits))


def coalesce(bits):
    """
    Take a sequence of bits, most significant first, and
    coalesce them into a number.

    >>> coalesce([1,0,1])
    5
    """

    def operation(a, b):
        return a << 1 | b

    return reduce(operation, bits)


class Flags:
    """
    Subclasses should define _names, a list of flag names beginning
    with the least-significant bit.

    >>> class MyFlags(Flags):
    ...     _names = 'a', 'b', 'c'
    >>> mf = MyFlags.from_number(5)
    >>> mf['a']
    1
    >>> mf['b']
    0
    >>> mf['c'] == mf[2]
    True
    >>> mf['b'] = 1
    >>> mf['a'] = 0
    >>> mf.number
    6
    """

    def __init__(self, values):
        self._values = list(values)
        if hasattr(self, '_names'):
            n_missing_bits = len(self._names) - len(self._values)
            self._values.extend([0] * n_missing_bits)

    @classmethod
    def from_number(cls, number):
        return cls(gen_bit_values(number))

    @property
    def number(self):
        return coalesce(reversed(self._values))

    def __setitem__(self, key, value):
        # first try by index, then by name
        try:
            self._values[key] = value
        except TypeError:
            index = self._names.index(key)
            self._values[index] = value

    def __getitem__(self, key):
        # first try by index, then by name
        try:
            return self._values[key]
        except TypeError:
            index = self._names.index(key)
            return self._values[index]


class BitMask(type):
    """
    A metaclass to create a bitmask with attributes. Subclass an int and
    set this as the metaclass to use.

    Construct such a class:

    >>> class MyBits(int, metaclass=BitMask):
    ...     a = 0x1
    ...     b = 0x4
    ...     c = 0x3

    >>> b1 = MyBits(3)
    >>> b1.a, b1.b, b1.c
    (True, False, True)
    >>> b2 = MyBits(8)
    >>> any([b2.a, b2.b, b2.c])
    False

    If the instance defines methods, they won't be wrapped in
    properties.

    >>> class MyBits(int, metaclass=BitMask):
    ...     a = 0x1
    ...     b = 0x4
    ...     c = 0x3
    ...
    ...     @classmethod
    ...     def get_value(cls):
    ...         return 'some value'
    ...
    ...     @property
    ...     def prop(cls):
    ...         return 'a property'
    >>> MyBits(3).get_value()
    'some value'
    >>> MyBits(3).prop
    'a property'
    """

    def __new__(cls, name, bases, attrs):
        def make_property(name, value):
            if name.startswith('_') or not isinstance(value, numbers.Number):
                return value
            return property(lambda self, value=value: bool(self & value))

        newattrs = dict(
            (name, make_property(name, value)) for name, value in attrs.items()
        )
        return type.__new__(cls, name, bases, newattrs)
