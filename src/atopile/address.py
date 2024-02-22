"""
Addresses are references to a specific node.
They take the form: "path/to/file.ato:Entry.Path::instance.path"
Addresses go by other names in various files for historical reasons - but should be upgraded.

This file provides utilities for working with addresses.
"""
from typing import Optional, Iterable
from functools import wraps


class AddrStr(str):
    """
    Represents address strings
    """


def _handle_windows(func):
    """
    A decorator to handle windows paths

    FIXME: this is a hack to make this work under Windows
    until we come up with something better
    """

    @wraps(func)
    def wrapper(address: AddrStr, *args, **kwargs):
        if len(address) >= 2 and address[1] == ":" and address[0].isalpha():
            drive_letter = address[0]
            remainder = address[2:]
            result: Optional[str] = func(remainder, *args, **kwargs)
            if result is None:
                return None

            char_1 = result[0]
            if not (char_1 == "/" or char_1 == "\\"):
                return result

            return ":".join([drive_letter, result])
        return func(address, *args, **kwargs)

    return wrapper


@_handle_windows
def get_file(address: AddrStr) -> str:
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


def get_relative_addr_str(address: AddrStr) -> AddrStr:
    """
    Extract the relative address starting with the .ato file
    /abs/path/to/file.ato:Entry.Path::instance.path -> file.ato:Entry.Path::instance.path

    FIXME: relative is a little misleading, as it's not relative to anything in particular,
    it's merely the address without the absolute path.
    """
    return address.split("/")[-1]


def get_entry(address: AddrStr) -> AddrStr:
    """
    Extract the root path from an address.
    """
    return address.split("::")[0]


@_handle_windows
def get_entry_section(address: AddrStr) -> Optional[str]:
    """
    Extract the root path from an address.
    """
    try:
        return address.split(":")[1]
    except IndexError:
        return None


@_handle_windows
def get_instance_section(address: AddrStr) -> Optional[str]:
    """
    Extract the node path from an address.
    """
    try:
        return address.split(":")[3]
    except IndexError:
        return None


def get_name(address: AddrStr) -> str:
    """
    Extract name from the end of the sequence.
    """
    return address.split(":")[-1].split(".")[-1]


def add_instance(address: AddrStr, instance: str) -> AddrStr:
    """
    Add an instance to an address.
    """
    assert isinstance(instance, str)

    if not get_instance_section(address):
        return address + "::" + instance
    else:
        return address + "." + instance


def add_instances(address: AddrStr, instances: Iterable[str]) -> AddrStr:
    """
    Add multiple instances to an address.
    """
    assert not isinstance(instances, str)
    for instance in instances:
        address = add_instance(address, instance)
    return address


def add_entry(address: AddrStr, entry: str) -> AddrStr:
    """
    Add an entry to an address.
    """
    assert isinstance(entry, str)

    if get_instance_section(address):
        raise ValueError("Cannot add entry to an instance address.")

    if not get_entry_section(address):
        return address + ":" + entry
    else:
        return address + "." + entry


def add_entries(address: AddrStr, entries: Iterable[str]) -> AddrStr:
    """
    Add multiple entries to an address.
    """
    assert not isinstance(entries, str)
    for entry in entries:
        address = add_entry(address, entry)
    return address


def from_parts(
    file: str, entry: Optional[str] = None, instance: Optional[str] = None
) -> AddrStr:
    """
    Create an address from its parts.
    """
    address = file
    if entry:
        address = add_entry(address, entry)
    if instance:
        address = add_instance(address, instance)
    return address
