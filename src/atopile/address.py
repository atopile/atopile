"""
Addresses are references to a specific node.
They take the form: "path/to/file.ato:Entry.Path::instance.path"
Addresses go by other names in various files for historical reasons,
but should be upgraded.

This file provides utilities for working with addresses.
"""

import os
from functools import wraps
from os import PathLike
from pathlib import Path
from typing import Iterable, Optional


class AddrStr(str):
    """
    Represents address strings
    """

    @property
    def file_path(self) -> Path:
        return Path(get_file(self))

    @property
    def entry_section(self) -> str:
        if entry_section := get_entry_section(self):
            return entry_section
        raise AddressError("No entry section in address")

    @classmethod
    def from_parts(
        cls,
        file: str | os.PathLike | None,
        entry: str | None = None,
        instance: str | None = None,
    ) -> "AddrStr":
        return cls(from_parts(file, entry, instance))


class AddressError(ValueError):
    """
    Base class for address errors
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


def get_relative_addr_str(address: AddrStr, base_path: PathLike) -> AddrStr:
    """
    Extract the relative address starting with the .ato file
    /abs/path/to/file.ato:Entry.Path::instance.path
        -> file.ato:Entry.Path::instance.path

    FIXME: this is the first and currently only place we're
    using these relative addresses. We should codify them
    """
    rel_file = Path(get_file(address)).relative_to(base_path)
    return from_parts(
        str(rel_file), get_entry_section(address), get_instance_section(address)
    )


def get_entry(address: AddrStr) -> str:
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
    if not instance:
        return address

    current_instance_addr = get_instance_section(address)
    if current_instance_addr is not None:
        if current_instance_addr == "":
            return AddrStr(address + instance)
        return AddrStr(address + "." + instance)
    elif get_entry_section(address):
        return AddrStr(address + "::" + instance)
    else:
        raise AddressError("Cannot add instance to something without an entry section.")


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
        raise AddressError("Cannot add entry to an instance address.")

    if not get_entry_section(address):
        return AddrStr(address + ":" + entry)
    else:
        return AddrStr(address + "." + entry)


def add_entries(address: AddrStr, entries: Iterable[str]) -> AddrStr:
    """
    Add multiple entries to an address.
    """
    assert not isinstance(entries, str)
    for entry in entries:
        address = add_entry(address, entry)
    return address


def from_parts(
    file: str | None | os.PathLike,
    entry: str | None = None,
    instance: str | None = None,
) -> AddrStr:
    """
    Create an address from its parts.
    """
    address = AddrStr(file) if file else AddrStr("")
    if entry:
        address = add_entry(address, entry)
    if instance:
        address = add_instance(address, instance)
    return address


def get_parent_instance_addr(address: AddrStr) -> Optional[AddrStr]:
    """
    Get the parent instance of an address, returning None if it doesn't exist.
    """
    instance_section = get_instance_section(address)
    if instance_section is None:
        return None

    if "." in instance_section:
        return AddrStr(address.rsplit(".", 1)[0])

    return AddrStr(address.rsplit("::", 1)[0])


def get_instance_names(address: AddrStr) -> list[str]:
    """
    Get the instances of an address.
    """
    if instance_section := get_instance_section(address):
        return instance_section.split(".")
    return []
