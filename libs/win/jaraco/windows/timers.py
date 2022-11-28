"""
timers
    In particular, contains a waitable timer.
"""

import time
import _thread

from jaraco.windows.api import event as win32event


class WaitableTimer:
    """
    t = WaitableTimer()
    t.set(None, 10) # every 10 seconds
    t.wait_for_signal() # 10 seconds elapses
    t.stop()
    t.wait_for_signal(20) # 20 seconds elapses (timeout occurred)
    """

    def __init__(self):
        self.signal_event = win32event.CreateEvent(None, 0, 0, None)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

    def set(self, due_time, period):
        _thread.start_new_thread(self._signal_loop, (due_time, period))

    def stop(self):
        win32event.SetEvent(self.stop_event)

    def wait_for_signal(self, timeout=None):
        """
        wait for the signal; return after the signal has occurred or the
        timeout in seconds elapses.
        """
        timeout_ms = int(timeout * 1000) if timeout else win32event.INFINITE
        win32event.WaitForSingleObject(self.signal_event, timeout_ms)

    def _signal_loop(self, due_time, period):
        if not due_time and not period:
            raise ValueError("due_time or period must be non-zero")
        try:
            if not due_time:
                due_time = time.time() + period
            if due_time:
                self._wait(due_time - time.time())
            while period:
                due_time += period
                self._wait(due_time - time.time())
        except Exception:
            pass

    def _wait(self, seconds):
        milliseconds = int(seconds * 1000)
        if milliseconds > 0:
            res = win32event.WaitForSingleObject(self.stop_event, milliseconds)
            if res == win32event.WAIT_OBJECT_0:
                raise Exception
            if res == win32event.WAIT_TIMEOUT:
                pass
        win32event.SetEvent(self.signal_event)

    @staticmethod
    def get_even_due_time(period):
        now = time.time()
        return now - (now % period)
