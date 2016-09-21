from __future__ import unicode_literals

import six


class NonDataProperty(object):
	"""Much like the property builtin, but only implements __get__,
	making it a non-data property, and can be subsequently reset.

	See http://users.rcn.com/python/download/Descriptor.htm for more
	information.

	>>> class X(object):
	...   @NonDataProperty
	...   def foo(self):
	...     return 3
	>>> x = X()
	>>> x.foo
	3
	>>> x.foo = 4
	>>> x.foo
	4
	"""

	def __init__(self, fget):
		assert fget is not None, "fget cannot be none"
		assert six.callable(fget), "fget must be callable"
		self.fget = fget

	def __get__(self, obj, objtype=None):
		if obj is None:
			return self
		return self.fget(obj)


# from http://stackoverflow.com/a/5191224
class ClassPropertyDescriptor(object):

	def __init__(self, fget, fset=None):
		self.fget = fget
		self.fset = fset

	def __get__(self, obj, klass=None):
		if klass is None:
			klass = type(obj)
		return self.fget.__get__(obj, klass)()

	def __set__(self, obj, value):
		if not self.fset:
			raise AttributeError("can't set attribute")
		type_ = type(obj)
		return self.fset.__get__(obj, type_)(value)

	def setter(self, func):
		if not isinstance(func, (classmethod, staticmethod)):
			func = classmethod(func)
		self.fset = func
		return self


def classproperty(func):
	if not isinstance(func, (classmethod, staticmethod)):
		func = classmethod(func)

	return ClassPropertyDescriptor(func)
