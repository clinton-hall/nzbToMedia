import struct
import ctypes.wintypes
from ctypes.wintypes import DWORD, WCHAR, BYTE, BOOL


# from mprapi.h
MAX_INTERFACE_NAME_LEN = 2 ** 8

# from iprtrmib.h
MAXLEN_PHYSADDR = 2 ** 3
MAXLEN_IFDESCR = 2 ** 8

# from iptypes.h
MAX_ADAPTER_ADDRESS_LENGTH = 8
MAX_DHCPV6_DUID_LENGTH = 130


class MIB_IFROW(ctypes.Structure):
    _fields_ = (
        ('name', WCHAR * MAX_INTERFACE_NAME_LEN),
        ('index', DWORD),
        ('type', DWORD),
        ('MTU', DWORD),
        ('speed', DWORD),
        ('physical_address_length', DWORD),
        ('physical_address_raw', BYTE * MAXLEN_PHYSADDR),
        ('admin_status', DWORD),
        ('operational_status', DWORD),
        ('last_change', DWORD),
        ('octets_received', DWORD),
        ('unicast_packets_received', DWORD),
        ('non_unicast_packets_received', DWORD),
        ('incoming_discards', DWORD),
        ('incoming_errors', DWORD),
        ('incoming_unknown_protocols', DWORD),
        ('octets_sent', DWORD),
        ('unicast_packets_sent', DWORD),
        ('non_unicast_packets_sent', DWORD),
        ('outgoing_discards', DWORD),
        ('outgoing_errors', DWORD),
        ('outgoing_queue_length', DWORD),
        ('description_length', DWORD),
        ('description_raw', ctypes.c_char * MAXLEN_IFDESCR),
    )

    def _get_binary_property(self, name):
        val_prop = '{0}_raw'.format(name)
        val = getattr(self, val_prop)
        len_prop = '{0}_length'.format(name)
        length = getattr(self, len_prop)
        return str(memoryview(val))[:length]

    @property
    def physical_address(self):
        return self._get_binary_property('physical_address')

    @property
    def description(self):
        return self._get_binary_property('description')


class MIB_IFTABLE(ctypes.Structure):
    _fields_ = (
        ('num_entries', DWORD),  # dwNumEntries
        ('entries', MIB_IFROW * 0),  # table
    )


class MIB_IPADDRROW(ctypes.Structure):
    _fields_ = (
        ('address_num', DWORD),
        ('index', DWORD),
        ('mask', DWORD),
        ('broadcast_address', DWORD),
        ('reassembly_size', DWORD),
        ('unused', ctypes.c_ushort),
        ('type', ctypes.c_ushort),
    )

    @property
    def address(self):
        "The address in big-endian"
        _ = struct.pack('L', self.address_num)
        return struct.unpack('!L', _)[0]


class MIB_IPADDRTABLE(ctypes.Structure):
    _fields_ = (('num_entries', DWORD), ('entries', MIB_IPADDRROW * 0))


class SOCKADDR(ctypes.Structure):
    _fields_ = (('family', ctypes.c_ushort), ('data', ctypes.c_byte * 14))


LPSOCKADDR = ctypes.POINTER(SOCKADDR)


class SOCKET_ADDRESS(ctypes.Structure):
    _fields_ = [('address', LPSOCKADDR), ('length', ctypes.c_int)]


class _IP_ADAPTER_ADDRESSES_METRIC(ctypes.Structure):
    _fields_ = [('length', ctypes.c_ulong), ('interface_index', DWORD)]


class _IP_ADAPTER_ADDRESSES_U1(ctypes.Union):
    _fields_ = [
        ('alignment', ctypes.c_ulonglong),
        ('metric', _IP_ADAPTER_ADDRESSES_METRIC),
    ]


class IP_ADAPTER_ADDRESSES(ctypes.Structure):
    pass


LP_IP_ADAPTER_ADDRESSES = ctypes.POINTER(IP_ADAPTER_ADDRESSES)

# for now, just use void * for pointers to unused structures
PIP_ADAPTER_UNICAST_ADDRESS = ctypes.c_void_p
PIP_ADAPTER_ANYCAST_ADDRESS = ctypes.c_void_p
PIP_ADAPTER_MULTICAST_ADDRESS = ctypes.c_void_p
PIP_ADAPTER_DNS_SERVER_ADDRESS = ctypes.c_void_p
PIP_ADAPTER_PREFIX = ctypes.c_void_p
PIP_ADAPTER_WINS_SERVER_ADDRESS_LH = ctypes.c_void_p
PIP_ADAPTER_GATEWAY_ADDRESS_LH = ctypes.c_void_p
PIP_ADAPTER_DNS_SUFFIX = ctypes.c_void_p

IF_OPER_STATUS = ctypes.c_uint  # this is an enum, consider
# http://code.activestate.com/recipes/576415/
IF_LUID = ctypes.c_uint64

NET_IF_COMPARTMENT_ID = ctypes.c_uint32
GUID = ctypes.c_byte * 16
NET_IF_NETWORK_GUID = GUID
NET_IF_CONNECTION_TYPE = ctypes.c_uint  # enum
TUNNEL_TYPE = ctypes.c_uint  # enum

IP_ADAPTER_ADDRESSES._fields_ = [
    # ('u', _IP_ADAPTER_ADDRESSES_U1),
    ('length', ctypes.c_ulong),
    ('interface_index', DWORD),
    ('next', LP_IP_ADAPTER_ADDRESSES),
    ('adapter_name', ctypes.c_char_p),
    ('first_unicast_address', PIP_ADAPTER_UNICAST_ADDRESS),
    ('first_anycast_address', PIP_ADAPTER_ANYCAST_ADDRESS),
    ('first_multicast_address', PIP_ADAPTER_MULTICAST_ADDRESS),
    ('first_dns_server_address', PIP_ADAPTER_DNS_SERVER_ADDRESS),
    ('dns_suffix', ctypes.c_wchar_p),
    ('description', ctypes.c_wchar_p),
    ('friendly_name', ctypes.c_wchar_p),
    ('byte', BYTE * MAX_ADAPTER_ADDRESS_LENGTH),
    ('physical_address_length', DWORD),
    ('flags', DWORD),
    ('mtu', DWORD),
    ('interface_type', DWORD),
    ('oper_status', IF_OPER_STATUS),
    ('ipv6_interface_index', DWORD),
    ('zone_indices', DWORD),
    ('first_prefix', PIP_ADAPTER_PREFIX),
    ('transmit_link_speed', ctypes.c_uint64),
    ('receive_link_speed', ctypes.c_uint64),
    ('first_wins_server_address', PIP_ADAPTER_WINS_SERVER_ADDRESS_LH),
    ('first_gateway_address', PIP_ADAPTER_GATEWAY_ADDRESS_LH),
    ('ipv4_metric', ctypes.c_ulong),
    ('ipv6_metric', ctypes.c_ulong),
    ('luid', IF_LUID),
    ('dhcpv4_server', SOCKET_ADDRESS),
    ('compartment_id', NET_IF_COMPARTMENT_ID),
    ('network_guid', NET_IF_NETWORK_GUID),
    ('connection_type', NET_IF_CONNECTION_TYPE),
    ('tunnel_type', TUNNEL_TYPE),
    ('dhcpv6_server', SOCKET_ADDRESS),
    ('dhcpv6_client_duid', ctypes.c_byte * MAX_DHCPV6_DUID_LENGTH),
    ('dhcpv6_client_duid_length', ctypes.c_ulong),
    ('dhcpv6_iaid', ctypes.c_ulong),
    ('first_dns_suffix', PIP_ADAPTER_DNS_SUFFIX),
]

# define some parameters to the API Functions
GetIfTable = ctypes.windll.iphlpapi.GetIfTable
GetIfTable.argtypes = [
    ctypes.POINTER(MIB_IFTABLE),
    ctypes.POINTER(ctypes.c_ulong),
    BOOL,
]
GetIfTable.restype = DWORD

GetIpAddrTable = ctypes.windll.iphlpapi.GetIpAddrTable
GetIpAddrTable.argtypes = [
    ctypes.POINTER(MIB_IPADDRTABLE),
    ctypes.POINTER(ctypes.c_ulong),
    BOOL,
]
GetIpAddrTable.restype = DWORD

GetAdaptersAddresses = ctypes.windll.iphlpapi.GetAdaptersAddresses
GetAdaptersAddresses.argtypes = [
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_void_p,
    ctypes.POINTER(IP_ADAPTER_ADDRESSES),
    ctypes.POINTER(ctypes.c_ulong),
]
GetAdaptersAddresses.restype = ctypes.c_ulong
