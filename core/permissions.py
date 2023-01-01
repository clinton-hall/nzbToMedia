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
    stat_result = os.stat(path)  # Get information from path
    permissions_mask = 0o777  # Set mask for permissions info

    # Get only the permissions part of st_mode as an integer
    int_mode = stat_result.st_mode & permissions_mask
    oct_mode = oct(int_mode)  # Convert to octal representation

    return oct_mode[2:]  # Return mode but strip octal prefix


def nt_ownership(path):
    """Get the owner and group for a file or directory."""
    def fully_qualified_name(sid):
        """Return a fully qualified account name."""
        # Look up the account information for the given SID
        # https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-lookupaccountsida
        name, domain, _acct_type = LookupAccountSid(None, sid)
        # Return account information formatted as DOMAIN\ACCOUNT_NAME
        return '{}\\{}'.format(domain, name)

    # Get the Windows security descriptor for the path
    # https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getnamedsecurityinfoa
    security_descriptor = GetNamedSecurityInfo(
        path,  # Name of the item to query
        SE_FILE_OBJECT,  # Type of item to query (file or directory)
        # Add OWNER and GROUP security information to result
        OWNER_SECURITY_INFORMATION | GROUP_SECURITY_INFORMATION,
    )
    # Get the Security Identifier for the owner and group from the security descriptor
    # https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-getsecuritydescriptorowner
    # https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-getsecuritydescriptorgroup
    owner_sid = security_descriptor.GetSecurityDescriptorOwner()
    group_sid = security_descriptor.GetSecurityDescriptorGroup()

    # Get the fully qualified account name (e.g. DOMAIN\ACCOUNT_NAME)
    owner = fully_qualified_name(owner_sid)
    group = fully_qualified_name(group_sid)

    return owner, group


def posix_ownership(path):
    """Get the owner and group for a file or directory."""
    # Get path information
    stat_result = os.stat(path)

    # Get account name from path stat result
    owner = pwd.getpwuid(stat_result.st_uid).pw_name
    group = grp.getgrgid(stat_result.st_gid).gr_name

    return owner, group


# Select the ownership function appropriate for the platform
if WINDOWS:
    ownership = nt_ownership
else:
    ownership = posix_ownership
