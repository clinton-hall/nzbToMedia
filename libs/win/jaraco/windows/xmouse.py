import ctypes
from jaraco.windows.error import handle_nonzero_success
from jaraco.windows.api import system
from jaraco.ui.cmdline import Command


def set(value):
    result = system.SystemParametersInfo(
        system.SPI_SETACTIVEWINDOWTRACKING, 0, ctypes.cast(value, ctypes.c_void_p), 0
    )
    handle_nonzero_success(result)


def get():
    value = ctypes.wintypes.BOOL()
    result = system.SystemParametersInfo(
        system.SPI_GETACTIVEWINDOWTRACKING, 0, ctypes.byref(value), 0
    )
    handle_nonzero_success(result)
    return bool(value)


def set_delay(milliseconds):
    result = system.SystemParametersInfo(
        system.SPI_SETACTIVEWNDTRKTIMEOUT,
        0,
        ctypes.cast(milliseconds, ctypes.c_void_p),
        0,
    )
    handle_nonzero_success(result)


def get_delay():
    value = ctypes.wintypes.DWORD()
    result = system.SystemParametersInfo(
        system.SPI_GETACTIVEWNDTRKTIMEOUT, 0, ctypes.byref(value), 0
    )
    handle_nonzero_success(result)
    return int(value.value)


class DelayParam(Command):
    @staticmethod
    def add_arguments(parser):
        parser.add_argument(
            '-d',
            '--delay',
            type=int,
            help="Delay in milliseconds for active window tracking",
        )


class Show(Command):
    @classmethod
    def run(cls, args):
        msg = "xmouse: {enabled} (delay {delay}ms)".format(
            enabled=get(), delay=get_delay()
        )
        print(msg)


class Enable(DelayParam):
    @classmethod
    def run(cls, args):
        print("enabling xmouse")
        set(True)
        args.delay and set_delay(args.delay)


class Disable(DelayParam):
    @classmethod
    def run(cls, args):
        print("disabling xmouse")
        set(False)
        args.delay and set_delay(args.delay)


class Toggle(DelayParam):
    @classmethod
    def run(cls, args):
        value = get()
        print("xmouse: %s -> %s" % (value, not value))
        set(not value)
        args.delay and set_delay(args.delay)


if __name__ == '__main__':
    Command.invoke()
