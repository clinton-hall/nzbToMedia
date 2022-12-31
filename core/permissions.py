import os
import sys
import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

WINDOWS = sys.platform == 'win32'
POSIX = not WINDOWS

try:
    import pwd
    import grp
except ImportError:
    if POSIX:
        raise

try:
    from win32security import GetNamedSecurityInfo
    from win32security import LookupAccountSid
    from win32security import GROUP_SECURITY_INFORMATION
    from win32security import OWNER_SECURITY_INFORMATION
    from win32security import SE_FILE_OBJECT
except ImportError:
    if WINDOWS:
        raise


def mode(path):
    """Get permissions."""
    return oct(os.stat(path).st_mode & 0o777)


def nt_ownership(path):
    """Get the owner and group for a file or directory."""
    def fully_qualified_name(sid):
        """Return a fully qualified account name."""
        name, domain, _acct_type = LookupAccountSid(None, sid)
        return '{}\\{}'.format(domain, name)

    security_descriptor = GetNamedSecurityInfo(
        os.fspath(path),
        SE_FILE_OBJECT,
        OWNER_SECURITY_INFORMATION | GROUP_SECURITY_INFORMATION,
    )
    owner_sid = security_descriptor.GetSecurityDescriptorOwner()
    group_sid = security_descriptor.GetSecurityDescriptorGroup()
    owner = fully_qualified_name(owner_sid)
    group = fully_qualified_name(group_sid)
    return owner, group


def posix_ownership(path):
    """Get the owner and group for a file or directory."""
    stat_result = os.stat(path)
    owner = pwd.getpwuid(stat_result.st_uid)
    group = grp.getgrgid(stat_result.st_gid)
    return owner, group


if WINDOWS:
    ownership = nt_ownership
else:
    ownership = posix_ownership
