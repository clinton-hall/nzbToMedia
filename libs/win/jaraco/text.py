from __future__ import absolute_import, unicode_literals, print_function

import sys
import re
import inspect
import itertools
import textwrap
import functools

import six

import jaraco.collections
from jaraco.functools import compose


def substitution(old, new):
	"""
	Return a function that will perform a substitution on a string
	"""
	return lambda s: s.replace(old, new)


def multi_substitution(*substitutions):
	"""
	Take a sequence of pairs specifying substitutions, and create
	a function that performs those substitutions.

	>>> multi_substitution(('foo', 'bar'), ('bar', 'baz'))('foo')
	'baz'
	"""
	substitutions = itertools.starmap(substitution, substitutions)
	# compose function applies last function first, so reverse the
	#  substitutions to get the expected order.
	substitutions = reversed(tuple(substitutions))
	return compose(*substitutions)


class FoldedCase(six.text_type):
	"""
	A case insensitive string class; behaves just like str
	except compares equal when the only variation is case.

	>>> s = FoldedCase('hello world')

	>>> s == 'Hello World'
	True

	>>> 'Hello World' == s
	True

	>>> s != 'Hello World'
	False

	>>> s.index('O')
	4

	>>> s.split('O')
	['hell', ' w', 'rld']

	>>> sorted(map(FoldedCase, ['GAMMA', 'alpha', 'Beta']))
	['alpha', 'Beta', 'GAMMA']

	Sequence membership is straightforward.

	>>> "Hello World" in [s]
	True
	>>> s in ["Hello World"]
	True

	You may test for set inclusion, but candidate and elements
	must both be folded.

	>>> FoldedCase("Hello World") in {s}
	True
	>>> s in {FoldedCase("Hello World")}
	True

	String inclusion works as long as the FoldedCase object
	is on the right.

	>>> "hello" in FoldedCase("Hello World")
	True

	But not if the FoldedCase object is on the left:

	>>> FoldedCase('hello') in 'Hello World'
	False

	In that case, use in_:

	>>> FoldedCase('hello').in_('Hello World')
	True

	"""
	def __lt__(self, other):
		return self.lower() < other.lower()

	def __gt__(self, other):
		return self.lower() > other.lower()

	def __eq__(self, other):
		return self.lower() == other.lower()

	def __ne__(self, other):
		return self.lower() != other.lower()

	def __hash__(self):
		return hash(self.lower())

	def __contains__(self, other):
		return super(FoldedCase, self).lower().__contains__(other.lower())

	def in_(self, other):
		"Does self appear in other?"
		return self in FoldedCase(other)

	# cache lower since it's likely to be called frequently.
	@jaraco.functools.method_cache
	def lower(self):
		return super(FoldedCase, self).lower()

	def index(self, sub):
		return self.lower().index(sub.lower())

	def split(self, splitter=' ', maxsplit=0):
		pattern = re.compile(re.escape(splitter), re.I)
		return pattern.split(self, maxsplit)


def local_format(string):
	"""
	format the string using variables in the caller's local namespace.

	>>> a = 3
	>>> local_format("{a:5}")
	'    3'
	"""
	context = inspect.currentframe().f_back.f_locals
	if sys.version_info < (3, 2):
		return string.format(**context)
	return string.format_map(context)


def global_format(string):
	"""
	format the string using variables in the caller's global namespace.

	>>> a = 3
	>>> fmt = "The func name: {global_format.__name__}"
	>>> global_format(fmt)
	'The func name: global_format'
	"""
	context = inspect.currentframe().f_back.f_globals
	if sys.version_info < (3, 2):
		return string.format(**context)
	return string.format_map(context)


def namespace_format(string):
	"""
	Format the string using variable in the caller's scope (locals + globals).

	>>> a = 3
	>>> fmt = "A is {a} and this func is {namespace_format.__name__}"
	>>> namespace_format(fmt)
	'A is 3 and this func is namespace_format'
	"""
	context = jaraco.collections.DictStack()
	context.push(inspect.currentframe().f_back.f_globals)
	context.push(inspect.currentframe().f_back.f_locals)
	if sys.version_info < (3, 2):
		return string.format(**context)
	return string.format_map(context)


def is_decodable(value):
	r"""
	Return True if the supplied value is decodable (using the default
	encoding).

	>>> is_decodable(b'\xff')
	False
	>>> is_decodable(b'\x32')
	True
	"""
	# TODO: This code could be expressed more consisely and directly
	# with a jaraco.context.ExceptionTrap, but that adds an unfortunate
	# long dependency tree, so for now, use boolean literals.
	try:
		value.decode()
	except UnicodeDecodeError:
		return False
	return True


def is_binary(value):
	"""
	Return True if the value appears to be binary (that is, it's a byte
	string and isn't decodable).
	"""
	return isinstance(value, bytes) and not is_decodable(value)


def trim(s):
	r"""
	Trim something like a docstring to remove the whitespace that
	is common due to indentation and formatting.

	>>> trim("\n\tfoo = bar\n\t\tbar = baz\n")
	'foo = bar\n\tbar = baz'
	"""
	return textwrap.dedent(s).strip()


class Splitter(object):
	"""object that will split a string with the given arguments for each call

	>>> s = Splitter(',')
	>>> s('hello, world, this is your, master calling')
	['hello', ' world', ' this is your', ' master calling']
	"""
	def __init__(self, *args):
		self.args = args

	def __call__(self, s):
		return s.split(*self.args)


def indent(string, prefix=' ' * 4):
	return prefix + string


class WordSet(tuple):
	"""
	Given a Python identifier, return the words that identifier represents,
	whether in camel case, underscore-separated, etc.

	>>> WordSet.parse("camelCase")
	('camel', 'Case')

	>>> WordSet.parse("under_sep")
	('under', 'sep')

	Acronyms should be retained

	>>> WordSet.parse("firstSNL")
	('first', 'SNL')

	>>> WordSet.parse("you_and_I")
	('you', 'and', 'I')

	>>> WordSet.parse("A simple test")
	('A', 'simple', 'test')

	Multiple caps should not interfere with the first cap of another word.

	>>> WordSet.parse("myABCClass")
	('my', 'ABC', 'Class')

	The result is a WordSet, so you can get the form you need.

	>>> WordSet.parse("myABCClass").underscore_separated()
	'my_ABC_Class'

	>>> WordSet.parse('a-command').camel_case()
	'ACommand'

	>>> WordSet.parse('someIdentifier').lowered().space_separated()
	'some identifier'

	Slices of the result should return another WordSet.

	>>> WordSet.parse('taken-out-of-context')[1:].underscore_separated()
	'out_of_context'

	>>> WordSet.from_class_name(WordSet()).lowered().space_separated()
	'word set'
	"""
	_pattern = re.compile('([A-Z]?[a-z]+)|([A-Z]+(?![a-z]))')

	def capitalized(self):
		return WordSet(word.capitalize() for word in self)

	def lowered(self):
		return WordSet(word.lower() for word in self)

	def camel_case(self):
		return ''.join(self.capitalized())

	def headless_camel_case(self):
		words = iter(self)
		first = next(words).lower()
		return itertools.chain((first,), WordSet(words).camel_case())

	def underscore_separated(self):
		return '_'.join(self)

	def dash_separated(self):
		return '-'.join(self)

	def space_separated(self):
		return ' '.join(self)

	def __getitem__(self, item):
		result = super(WordSet, self).__getitem__(item)
		if isinstance(item, slice):
			result = WordSet(result)
		return result

	# for compatibility with Python 2
	def __getslice__(self, i, j):
		return self.__getitem__(slice(i, j))

	@classmethod
	def parse(cls, identifier):
		matches = cls._pattern.finditer(identifier)
		return WordSet(match.group(0) for match in matches)

	@classmethod
	def from_class_name(cls, subject):
		return cls.parse(subject.__class__.__name__)


# for backward compatibility
words = WordSet.parse


def simple_html_strip(s):
	r"""
	Remove HTML from the string `s`.

	>>> str(simple_html_strip(''))
	''

	>>> print(simple_html_strip('A <bold>stormy</bold> day in paradise'))
	A stormy day in paradise

	>>> print(simple_html_strip('Somebody <!-- do not --> tell the truth.'))
	Somebody  tell the truth.

	>>> print(simple_html_strip('What about<br/>\nmultiple lines?'))
	What about
	multiple lines?
	"""
	html_stripper = re.compile('(<!--.*?-->)|(<[^>]*>)|([^<]+)', re.DOTALL)
	texts = (
		match.group(3) or ''
		for match
		in html_stripper.finditer(s)
	)
	return ''.join(texts)


class SeparatedValues(six.text_type):
	"""
	A string separated by a separator. Overrides __iter__ for getting
	the values.

	>>> list(SeparatedValues('a,b,c'))
	['a', 'b', 'c']

	Whitespace is stripped and empty values are discarded.

	>>> list(SeparatedValues(' a,   b   , c,  '))
	['a', 'b', 'c']
	"""
	separator = ','

	def __iter__(self):
		parts = self.split(self.separator)
		return six.moves.filter(None, (part.strip() for part in parts))


class Stripper:
	r"""
	Given a series of lines, find the common prefix and strip it from them.

	>>> lines = [
	...     'abcdefg\n',
	...     'abc\n',
	...     'abcde\n',
	... ]
	>>> res = Stripper.strip_prefix(lines)
	>>> res.prefix
	'abc'
	>>> list(res.lines)
	['defg\n', '\n', 'de\n']

	If no prefix is common, nothing should be stripped.

	>>> lines = [
	...     'abcd\n',
	...     '1234\n',
	... ]
	>>> res = Stripper.strip_prefix(lines)
	>>> res.prefix = ''
	>>> list(res.lines)
	['abcd\n', '1234\n']
	"""
	def __init__(self, prefix, lines):
		self.prefix = prefix
		self.lines = map(self, lines)

	@classmethod
	def strip_prefix(cls, lines):
		prefix_lines, lines = itertools.tee(lines)
		prefix = functools.reduce(cls.common_prefix, prefix_lines)
		return cls(prefix, lines)

	def __call__(self, line):
		if not self.prefix:
			return line
		null, prefix, rest = line.partition(self.prefix)
		return rest

	@staticmethod
	def common_prefix(s1, s2):
		"""
		Return the common prefix of two lines.
		"""
		index = min(len(s1), len(s2))
		while s1[:index] != s2[:index]:
			index -= 1
		return s1[:index]


def remove_prefix(text, prefix):
	"""
	Remove the prefix from the text if it exists.

	>>> remove_prefix('underwhelming performance', 'underwhelming ')
	'performance'

	>>> remove_prefix('something special', 'sample')
	'something special'
	"""
	null, prefix, rest = text.rpartition(prefix)
	return rest


def remove_suffix(text, suffix):
	"""
	Remove the suffix from the text if it exists.

	>>> remove_suffix('name.git', '.git')
	'name'

	>>> remove_suffix('something special', 'sample')
	'something special'
	"""
	rest, suffix, null = text.partition(suffix)
	return rest
