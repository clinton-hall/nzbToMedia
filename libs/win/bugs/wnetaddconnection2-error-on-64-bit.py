# reported at http://social.msdn.microsoft.com/Forums/en-US/wsk/thread/f43c2faf-3df3-4f11-9f5e-1a9101753f93
from win32wnet import WNetAddConnection2, NETRESOURCE

resource = NETRESOURCE()
resource.lpRemoteName = r'\\aoshi\users'
username = 'jaraco'
res = WNetAddConnection2(resource, UserName=username)
print('first result is', res)
res = WNetAddConnection2(resource, UserName=username)
print('second result is', res)

"""
Output is:

first result is None
Traceback (most recent call last):
  File ".\wnetaddconnection2-error-on-64-bit.py", line 7, in <module>
    res = WNetAddConnection2(resource, UserName=username)
pywintypes.error: (1219, 'WNetAddConnection2', 'Multiple connections to a server or shared resource by the same user, using more than one user name, are not allowed. Disconnect all previous connections to the server or shared resource and try again.')
"""
