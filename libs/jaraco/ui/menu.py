from __future__ import print_function, absolute_import, unicode_literals

import itertools

import six

class Menu(object):
	"""
	A simple command-line based menu
	"""
	def __init__(self, choices=None, formatter=str):
		self.choices = choices or list()
		self.formatter = formatter

	def get_choice(self, prompt="> "):
		n = len(self.choices)
		number_width = len(str(n)) + 1
		menu_fmt = '{number:{number_width}}) {choice}'
		formatted_choices = map(self.formatter, self.choices)
		for number, choice in zip(itertools.count(1), formatted_choices):
			print(menu_fmt.format(**locals()))
		print()
		try:
			answer = int(six.moves.input(prompt))
			result = self.choices[answer - 1]
		except ValueError:
			print('invalid selection')
			result = None
		except IndexError:
			print('invalid selection')
			result = None
		except KeyboardInterrupt:
			result = None
		return result
