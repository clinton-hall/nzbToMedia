"""
Some routines for retrieving the addresses from the local
network config.
"""

import itertools
import ctypes


from jaraco.windows.api import errors, inet


def GetAdaptersAddresses():
    size = ctypes.c_ulong()
    res = inet.GetAdaptersAddresses(0, 0, None, None, size)
    if res != errors.ERROR_BUFFER_OVERFLOW:
        raise RuntimeError("Error getting structure length (%d)" % res)
    print(size.value)
    pointer_type = ctypes.POINTER(inet.IP_ADAPTER_ADDRESSES)
    buffer = ctypes.create_string_buffer(size.value)
    struct_p = ctypes.cast(buffer, pointer_type)
    res = inet.GetAdaptersAddresses(0, 0, None, struct_p, size)
    if res != errors.NO_ERROR:
        raise RuntimeError("Error retrieving table (%d)" % res)
    while struct_p:
        yield struct_p.contents
        struct_p = struct_p.contents.next


class AllocatedTable(object):
    """
    Both the interface table and the ip address table use the same
    technique to store arrays of structures of variable length. This
    base class captures the functionality to retrieve and access those
    table entries.

    The subclass needs to define three class attributes:
        method: a callable that takes three arguments - a pointer to
                the structure, the length of the data contained by the
                structure, and a boolean of whether the result should
                be sorted.
        structure: a C structure defininition that describes the table
                format.
        row_structure: a C structure definition that describes the row
                format.
    """

    def __get_table_size(self):
        """
        Retrieve the size of the buffer needed by calling the method
        with a null pointer and length of zero. This should trigger an
        insufficient buffer error and return the size needed for the
        buffer.
        """
        length = ctypes.wintypes.DWORD()
        res = self.method(None, length, False)
        if res != errors.ERROR_INSUFFICIENT_BUFFER:
            raise RuntimeError("Error getting table length (%d)" % res)
        return length.value

    def get_table(self):
        """
        Get the table
        """
        buffer_length = self.__get_table_size()
        returned_buffer_length = ctypes.wintypes.DWORD(buffer_length)
        buffer = ctypes.create_string_buffer(buffer_length)
        pointer_type = ctypes.POINTER(self.structure)
        table_p = ctypes.cast(buffer, pointer_type)
        res = self.method(table_p, returned_buffer_length, False)
        if res != errors.NO_ERROR:
            raise RuntimeError("Error retrieving table (%d)" % res)
        return table_p.contents

    @property
    def entries(self):
        """
        Using the table structure, return the array of entries based
        on the table size.
        """
        table = self.get_table()
        entries_array = self.row_structure * table.num_entries
        pointer_type = ctypes.POINTER(entries_array)
        return ctypes.cast(table.entries, pointer_type).contents


class InterfaceTable(AllocatedTable):
    method = inet.GetIfTable
    structure = inet.MIB_IFTABLE
    row_structure = inet.MIB_IFROW


class AddressTable(AllocatedTable):
    method = inet.GetIpAddrTable
    structure = inet.MIB_IPADDRTABLE
    row_structure = inet.MIB_IPADDRROW


class AddressManager(object):
    @staticmethod
    def hardware_address_to_string(addr):
        hex_bytes = (byte.encode('hex') for byte in addr)
        return ':'.join(hex_bytes)

    def get_host_mac_address_strings(self):
        return (
            self.hardware_address_to_string(addr)
            for addr in self.get_host_mac_addresses()
        )

    def get_host_ip_address_strings(self):
        return itertools.imap(str, self.get_host_ip_addresses())

    def get_host_mac_addresses(self):
        return (entry.physical_address for entry in InterfaceTable().entries)

    def get_host_ip_addresses(self):
        return (entry.address for entry in AddressTable().entries)
