import ctypes.wintypes

# from WinNT.h
READ_CONTROL = 0x00020000
STANDARD_RIGHTS_REQUIRED = 0x000F0000
STANDARD_RIGHTS_READ = READ_CONTROL
STANDARD_RIGHTS_WRITE = READ_CONTROL
STANDARD_RIGHTS_EXECUTE = READ_CONTROL
STANDARD_RIGHTS_ALL = 0x001F0000

# from NTSecAPI.h
POLICY_VIEW_LOCAL_INFORMATION = 0x00000001
POLICY_VIEW_AUDIT_INFORMATION = 0x00000002
POLICY_GET_PRIVATE_INFORMATION = 0x00000004
POLICY_TRUST_ADMIN = 0x00000008
POLICY_CREATE_ACCOUNT = 0x00000010
POLICY_CREATE_SECRET = 0x00000020
POLICY_CREATE_PRIVILEGE = 0x00000040
POLICY_SET_DEFAULT_QUOTA_LIMITS = 0x00000080
POLICY_SET_AUDIT_REQUIREMENTS = 0x00000100
POLICY_AUDIT_LOG_ADMIN = 0x00000200
POLICY_SERVER_ADMIN = 0x00000400
POLICY_LOOKUP_NAMES = 0x00000800
POLICY_NOTIFICATION = 0x00001000

POLICY_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | POLICY_VIEW_LOCAL_INFORMATION
    | POLICY_VIEW_AUDIT_INFORMATION
    | POLICY_GET_PRIVATE_INFORMATION
    | POLICY_TRUST_ADMIN
    | POLICY_CREATE_ACCOUNT
    | POLICY_CREATE_SECRET
    | POLICY_CREATE_PRIVILEGE
    | POLICY_SET_DEFAULT_QUOTA_LIMITS
    | POLICY_SET_AUDIT_REQUIREMENTS
    | POLICY_AUDIT_LOG_ADMIN
    | POLICY_SERVER_ADMIN
    | POLICY_LOOKUP_NAMES
)


POLICY_READ = (
    STANDARD_RIGHTS_READ
    | POLICY_VIEW_AUDIT_INFORMATION
    | POLICY_GET_PRIVATE_INFORMATION
)

POLICY_WRITE = (
    STANDARD_RIGHTS_WRITE
    | POLICY_TRUST_ADMIN
    | POLICY_CREATE_ACCOUNT
    | POLICY_CREATE_SECRET
    | POLICY_CREATE_PRIVILEGE
    | POLICY_SET_DEFAULT_QUOTA_LIMITS
    | POLICY_SET_AUDIT_REQUIREMENTS
    | POLICY_AUDIT_LOG_ADMIN
    | POLICY_SERVER_ADMIN
)

POLICY_EXECUTE = (
    STANDARD_RIGHTS_EXECUTE | POLICY_VIEW_LOCAL_INFORMATION | POLICY_LOOKUP_NAMES
)


class TokenAccess:
    TOKEN_QUERY = 0x8


class TokenInformationClass:
    TokenUser = 1


class TOKEN_USER(ctypes.Structure):
    num = 1
    _fields_ = [('SID', ctypes.c_void_p), ('ATTRIBUTES', ctypes.wintypes.DWORD)]


class SECURITY_DESCRIPTOR(ctypes.Structure):
    """
    typedef struct _SECURITY_DESCRIPTOR
        {
        UCHAR Revision;
        UCHAR Sbz1;
        SECURITY_DESCRIPTOR_CONTROL Control;
        PSID Owner;
        PSID Group;
        PACL Sacl;
        PACL Dacl;
        }   SECURITY_DESCRIPTOR;
    """

    SECURITY_DESCRIPTOR_CONTROL = ctypes.wintypes.USHORT
    REVISION = 1

    _fields_ = [
        ('Revision', ctypes.c_ubyte),
        ('Sbz1', ctypes.c_ubyte),
        ('Control', SECURITY_DESCRIPTOR_CONTROL),
        ('Owner', ctypes.c_void_p),
        ('Group', ctypes.c_void_p),
        ('Sacl', ctypes.c_void_p),
        ('Dacl', ctypes.c_void_p),
    ]


class SECURITY_ATTRIBUTES(ctypes.Structure):
    """
    typedef struct _SECURITY_ATTRIBUTES {
        DWORD  nLength;
        LPVOID lpSecurityDescriptor;
        BOOL   bInheritHandle;
    } SECURITY_ATTRIBUTES;
    """

    _fields_ = [
        ('nLength', ctypes.wintypes.DWORD),
        ('lpSecurityDescriptor', ctypes.c_void_p),
        ('bInheritHandle', ctypes.wintypes.BOOL),
    ]

    def __init__(self, *args, **kwargs):
        super(SECURITY_ATTRIBUTES, self).__init__(*args, **kwargs)
        self.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)

    @property
    def descriptor(self):
        return self._descriptor

    @descriptor.setter
    def descriptor(self, value):
        self._descriptor = value
        self.lpSecurityDescriptor = ctypes.addressof(value)


ctypes.windll.advapi32.SetSecurityDescriptorOwner.argtypes = (
    ctypes.POINTER(SECURITY_DESCRIPTOR),
    ctypes.c_void_p,
    ctypes.wintypes.BOOL,
)
