"""
Addresses are references to a specific node.
They take the form: "path/to/file.ato:Entry.Path::instance.path"
Addresses go by other names in various files for historical reasons - but should be upgraded.

This file provides utilities for working with addresses.
"""
from typing import Optional


class AddrStr(str):
    """
    Represents address strings
    """


def get_file_section(address: AddrStr) -> str:
    """
    Extract the file path from an address.

    This will return None if there is no file address.
    FIXME: this is different to the node addresses,
    which will return an empty string or tuple if there
    is no node address.
    This is because an "empty" file path is a valid address,
    to the current working directory, which is confusing.
    """
    return address.split(":")[0]


def get_entry(address: AddrStr) -> AddrStr:
    """
    Extract the root path from an address.
    """
    return address.split("::")[0]


def get_entry_section(address: AddrStr) -> Optional[str]:
    """
    Extract the root path from an address.
    """
    try:
        return address.split(":")[1]
    except IndexError:
        return None


def get_instance_section(address: AddrStr) -> Optional[str]:
    """
    Extract the node path from an address.
    """
    try:
        return address.split(":")[3]
    except IndexError:
        return None


def add_instance(address: AddrStr, instance: str) -> AddrStr:
    """
    Add an instance to an address.
    """
    if not get_instance_section(address):
        return f"{address}::{instance}"
    else:
        return f"{address}.{instance}"


def add_entry(address: AddrStr, entry: str) -> AddrStr:
    """
    Add an entry to an address.
    """
    if get_instance_section(address):
        raise ValueError("Cannot add entry to an instance address.")

    if not get_entry_section(address):
        return f"{address}:{entry}"
    else:
        return f"{address}.{entry}"


def from_parts(file: str, entry: Optional[str] = None, instance: Optional[str] = None) -> AddrStr:
    """
    Create an address from its parts.
    """
    address = file
    if entry:
        address = add_entry(address, entry)
    if instance:
        address = add_instance(address, instance)
    return address
