"""cookies.py

Cookie support utilities
"""

import os
import itertools


class CookieMonster(object):
    "Read cookies out of a user's IE cookies file"

    @property
    def cookie_dir(self):
        import _winreg as winreg

        key = winreg.OpenKeyEx(
            winreg.HKEY_CURRENT_USER,
            'Software' r'\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders',
        )
        cookie_dir, type = winreg.QueryValueEx(key, 'Cookies')
        return cookie_dir

    def entries(self, filename):
        with open(os.path.join(self.cookie_dir, filename)) as cookie_file:
            while True:
                entry = itertools.takewhile(self.is_not_cookie_delimiter, cookie_file)
                entry = [item.rstrip() for item in entry]
                if not entry:
                    break
                cookie = self.make_cookie(*entry)
                yield cookie

    @staticmethod
    def is_not_cookie_delimiter(s):
        return s != '*\n'

    @staticmethod
    def make_cookie(
        key, value, domain, flags, ExpireLow, ExpireHigh, CreateLow, CreateHigh
    ):
        expires = (int(ExpireHigh) << 32) | int(ExpireLow)
        created = (int(CreateHigh) << 32) | int(CreateLow)
        flags = int(flags)
        domain, sep, path = domain.partition('/')
        path = '/' + path
        return dict(
            key=key,
            value=value,
            domain=domain,
            flags=flags,
            expires=expires,
            created=created,
            path=path,
        )
