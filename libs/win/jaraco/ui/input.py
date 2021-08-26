"""
This module currently provides a cross-platform getch function
"""

try:
	# Windows
	from msvcrt import getch
except ImportError:
	pass

try:
	# Unix
	import sys
	import tty
	import termios

	def getch():
		fd = sys.stdin.fileno()
		old = termios.tcgetattr(fd)
		try:
			tty.setraw(fd)
			return sys.stdin.read(1)
		finally:
			termios.tcsetattr(fd, termios.TCSADRAIN, old)
except ImportError:
	pass
