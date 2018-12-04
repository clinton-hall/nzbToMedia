from __future__ import (print_function, absolute_import, unicode_literals,
	division)

import time
import sys
import itertools
import abc
import datetime

import six


@six.add_metaclass(abc.ABCMeta)
class AbstractProgressBar(object):
	def __init__(self, unit='', size=70):
		"""
		Size is the nominal size in characters
		"""
		self.unit = unit
		self.size = size

	def report(self, amt):
		sys.stdout.write('\r%s' % self.get_bar(amt))
		sys.stdout.flush()

	@abc.abstractmethod
	def get_bar(self, amt):
		"Return the string to be printed. Should be size >= self.size"

	def summary(self, str):
		return ' (' + self.unit_str(str) + ')'

	def unit_str(self, str):
		if self.unit:
			str += ' ' + self.unit
		return str

	def finish(self):
		print()

	def __enter__(self):
		self.report(0)
		return self

	def __exit__(self, exc, exc_val, tb):
		if exc is None:
			self.finish()
		else:
			print()

	def iterate(self, iterable):
		"""
		Report the status as the iterable is consumed.
		"""
		with self:
			for n, item in enumerate(iterable, 1):
				self.report(n)
				yield item


class SimpleProgressBar(AbstractProgressBar):

	_PROG_DISPGLYPH = itertools.cycle(['|', '/', '-', '\\'])

	def get_bar(self, amt):
		bar = next(self._PROG_DISPGLYPH)
		template = ' [{bar:^{bar_len}}]'
		summary = self.summary('{amt}')
		template += summary
		empty = template.format(
			bar='',
			bar_len=0,
			amt=amt,
		)
		bar_len = self.size - len(empty)
		return template.format(**locals())

	@classmethod
	def demo(cls):
		bar3 = cls(unit='cubes', size=30)
		with bar3:
			for x in six.moves.range(1, 759):
				bar3.report(x)
				time.sleep(0.01)


class TargetProgressBar(AbstractProgressBar):
	def __init__(self, total=None, unit='', size=70):
		"""
		Size is the nominal size in characters
		"""
		self.total = total
		super(TargetProgressBar, self).__init__(unit, size)

	def get_bar(self, amt):
		template = ' [{bar:<{bar_len}}]'
		completed = amt / self.total
		percent = int(completed * 100)
		percent_str = ' {percent:3}%'
		template += percent_str
		summary = self.summary('{amt}/{total}')
		template += summary
		empty = template.format(
			total=self.total,
			bar='',
			bar_len=0,
			**locals()
		)
		bar_len = self.size - len(empty)
		bar = '=' * int(completed * bar_len)
		return template.format(total=self.total, **locals())

	@classmethod
	def demo(cls):
		bar1 = cls(100, 'blocks')
		with bar1:
			for x in six.moves.range(1, 101):
				bar1.report(x)
				time.sleep(0.05)

		bar2 = cls(758, size=50)
		with bar2:
			for x in six.moves.range(1, 759):
				bar2.report(x)
				time.sleep(0.01)

	def finish(self):
		self.report(self.total)
		super(TargetProgressBar, self).finish()


def countdown(template, duration=datetime.timedelta(seconds=5)):
	"""
	Do a countdown for duration, printing the template (which may accept one
	positional argument). Template should be something like
	``countdown complete in {} seconds.``
	"""
	now = datetime.datetime.now()
	deadline = now + duration
	remaining = deadline - datetime.datetime.now()
	while remaining:
		remaining = deadline - datetime.datetime.now()
		remaining = max(datetime.timedelta(), remaining)
		msg = template.format(remaining.total_seconds())
		print(msg, end=' '*10)
		sys.stdout.flush()
		time.sleep(.1)
		print('\b'*80, end='')
		sys.stdout.flush()
	print()
