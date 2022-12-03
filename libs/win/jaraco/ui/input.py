"""
This module currently provides a cross-platform getch function
"""

try:
    # Windows
    from msvcrt import getch  # type: ignore

    getch  # workaround for https://github.com/kevinw/pyflakes/issues/13
except ImportError:
    pass

try:
    # Unix
    import sys
    import tty
    import termios

    def getch():  # type: ignore
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


except ImportError:
    pass
