from __future__ import absolute_import, unicode_literals, print_function, division

import functools
import time
import warnings

try:
	from functools import lru_cache
except ImportError:
	try:
		from backports.functools_lru_cache import lru_cache
	except ImportError:
		try:
			from functools32 import lru_cache
		except ImportError:
			warnings.warn("No lru_cache available")


def compose(*funcs):
	"""
	Compose any number of unary functions into a single unary function.

	>>> import textwrap
	>>> from six import text_type
	>>> text_type.strip(textwrap.dedent(compose.__doc__)) == compose(text_type.strip, textwrap.dedent)(compose.__doc__)
	True

	Compose also allows the innermost function to take arbitrary arguments.

	>>> round_three = lambda x: round(x, ndigits=3)
	>>> f = compose(round_three, int.__truediv__)
	>>> [f(3*x, x+1) for x in range(1,10)]
	[1.5, 2.0, 2.25, 2.4, 2.5, 2.571, 2.625, 2.667, 2.7]
	"""

	compose_two = lambda f1, f2: lambda *args, **kwargs: f1(f2(*args, **kwargs))
	return functools.reduce(compose_two, funcs)


def method_caller(method_name, *args, **kwargs):
	"""
	Return a function that will call a named method on the
	target object with optional positional and keyword
	arguments.

	>>> lower = method_caller('lower')
	>>> lower('MyString')
	'mystring'
	"""
	def call_method(target):
		func = getattr(target, method_name)
		return func(*args, **kwargs)
	return call_method


def once(func):
	"""
	Decorate func so it's only ever called the first time.

	This decorator can ensure that an expensive or non-idempotent function
	will not be expensive on subsequent calls and is idempotent.

	>>> func = once(lambda a: a+3)
	>>> func(3)
	6
	>>> func(9)
	6
	>>> func('12')
	6
	"""
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		if not hasattr(func, 'always_returns'):
			func.always_returns = func(*args, **kwargs)
		return func.always_returns
	return wrapper


def method_cache(method, cache_wrapper=None):
	"""
	Wrap lru_cache to support storing the cache data in the object instances.

	Abstracts the common paradigm where the method explicitly saves an
	underscore-prefixed protected property on first call and returns that
	subsequently.

	>>> class MyClass:
	...     calls = 0
	...
	...     @method_cache
	...     def method(self, value):
	...         self.calls += 1
	...         return value

	>>> a = MyClass()
	>>> a.method(3)
	3
	>>> for x in range(75):
	...     res = a.method(x)
	>>> a.calls
	75

	Note that the apparent behavior will be exactly like that of lru_cache
	except that the cache is stored on each instance, so values in one
	instance will not flush values from another, and when an instance is
	deleted, so are the cached values for that instance.

	>>> b = MyClass()
	>>> for x in range(35):
	...     res = b.method(x)
	>>> b.calls
	35
	>>> a.method(0)
	0
	>>> a.calls
	75

	Note that if method had been decorated with ``functools.lru_cache()``,
	a.calls would have been 76 (due to the cached value of 0 having been
	flushed by the 'b' instance).

	Clear the cache with ``.cache_clear()``

	>>> a.method.cache_clear()

	Another cache wrapper may be supplied:

	>>> cache = lru_cache(maxsize=2)
	>>> MyClass.method2 = method_cache(lambda self: 3, cache_wrapper=cache)
	>>> a = MyClass()
	>>> a.method2()
	3

	See also
	http://code.activestate.com/recipes/577452-a-memoize-decorator-for-instance-methods/
	for another implementation and additional justification.
	"""
	cache_wrapper = cache_wrapper or lru_cache()
	def wrapper(self, *args, **kwargs):
		# it's the first call, replace the method with a cached, bound method
		bound_method = functools.partial(method, self)
		cached_method = cache_wrapper(bound_method)
		setattr(self, method.__name__, cached_method)
		return cached_method(*args, **kwargs)
	return _special_method_cache(method, cache_wrapper) or wrapper


def _special_method_cache(method, cache_wrapper):
	"""
	Because Python treats special methods differently, it's not
	possible to use instance attributes to implement the cached
	methods.

	Instead, install the wrapper method under a different name
	and return a simple proxy to that wrapper.

	https://github.com/jaraco/jaraco.functools/issues/5
	"""
	name = method.__name__
	special_names = '__getattr__', '__getitem__'
	if name not in special_names:
		return

	wrapper_name = '__cached' + name

	def proxy(self, *args, **kwargs):
		if wrapper_name not in vars(self):
			bound = functools.partial(method, self)
			cache = cache_wrapper(bound)
			setattr(self, wrapper_name, cache)
		else:
			cache = getattr(self, wrapper_name)
		return cache(*args, **kwargs)

	return proxy


def apply(transform):
	"""
	Decorate a function with a transform function that is
	invoked on results returned from the decorated function.

	>>> @apply(reversed)
	... def get_numbers(start):
	...     return range(start, start+3)
	>>> list(get_numbers(4))
	[6, 5, 4]
	"""
	def wrap(func):
		return compose(transform, func)
	return wrap


def call_aside(f, *args, **kwargs):
	"""
	Call a function for its side effect after initialization.

	>>> @call_aside
	... def func(): print("called")
	called
	>>> func()
	called

	Use functools.partial to pass parameters to the initial call

	>>> @functools.partial(call_aside, name='bingo')
	... def func(name): print("called with", name)
	called with bingo
	"""
	f(*args, **kwargs)
	return f


class Throttler(object):
	"""
	Rate-limit a function (or other callable)
	"""
	def __init__(self, func, max_rate=float('Inf')):
		if isinstance(func, Throttler):
			func = func.func
		self.func = func
		self.max_rate = max_rate
		self.reset()

	def reset(self):
		self.last_called = 0

	def __call__(self, *args, **kwargs):
		self._wait()
		return self.func(*args, **kwargs)

	def _wait(self):
		"ensure at least 1/max_rate seconds from last call"
		elapsed = time.time() - self.last_called
		must_wait = 1 / self.max_rate - elapsed
		time.sleep(max(0, must_wait))
		self.last_called = time.time()

	def __get__(self, obj, type=None):
		return first_invoke(self._wait, functools.partial(self.func, obj))


def first_invoke(func1, func2):
	"""
	Return a function that when invoked will invoke func1 without
	any parameters (for its side-effect) and then invoke func2
	with whatever parameters were passed, returning its result.
	"""
	def wrapper(*args, **kwargs):
		func1()
		return func2(*args, **kwargs)
	return wrapper


def retry_call(func, cleanup=lambda: None, retries=0, trap=()):
	"""
	Given a callable func, trap the indicated exceptions
	for up to 'retries' times, invoking cleanup on the
	exception. On the final attempt, allow any exceptions
	to propagate.
	"""
	for attempt in range(retries):
		try:
			return func()
		except trap:
			cleanup()

	return func()
