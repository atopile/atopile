"""
Addresses are references to a specific node.
They take the form: "path/to/file.ato:node.path"
Addresses go by other names in various files for historical reasons - but should be upgraded.

This file provides utilities for working with addresses.
"""
from pathlib import Path
from os import PathLike
from typing import Optional


class AddrValueError(ValueError):
    """
    Raised when an address is invalid.
    """


def get_file(address: str) -> Optional[Path]:
    """
    Extract the file path from an address.

    This will return None if there is no file address.
    FIXME: this is different to the node addresses,
    which will return an empty string or tuple if there
    is no node address.
    This is because an "empty" file path is a valid address,
    to the current working directory, which is confusing.
    """
    path_str = address.split(":")[0]
    if not path_str:
        return None
    return Path(path_str)


def get_node_str(address: str) -> str:
    """
    Extract the node path from an address.
    """
    try:
        return address.split(":")[1]
    except IndexError:
        return ""


def get_node_as_ref(address: str) -> tuple[str]:
    """
    Extract the node path from an address.
    """
    str_node = get_node_str(address)
    return tuple(str_node.split(".") if str_node else [])


def validate_address(address: str) -> None:
    """
    Validate an address, raising an exception if it is invalid.
    """
    # check there are 0 or 1 ":" in the string
    if address.count(":") > 1:
        raise AddrValueError(f"Address {address} has more than one ':'.")


def is_address_valid(address: str) -> bool:
    """
    Check if an address is valid, returning True if it is and False if it is not.
    """
    try:
        validate_address(address)
    except AddrValueError:
        return False
    return True


class AddrStr(str):
    """
    Thin wrapper class to represent specifically addresses.
    """

    @property
    def file(self) -> Optional[Path]:
        """Return the file section of the address as a Path."""
        return get_file(self)

    @property
    def node_as_str(self) -> str:
        """Return the node section of the address as a string."""
        return get_node_str(self)

    @property
    def node(self) -> tuple[str]:
        """Return the node section of the address as a reference"""
        return get_node_as_ref(self)

    @classmethod
    def from_str(cls, address: str) -> "AddrStr":
        """
        Create an address from a string and validates it.
        """
        validate_address(address)
        return cls(address)

    @classmethod
    def from_parts(
        cls,
        path: Optional[str | PathLike] = None,
        node: Optional[str | tuple[str]] = None
    ) -> "AddrStr":
        """
        Create an address from a path and a node.
        """
        if path is None:
            path = ""
        else:
            path = str(path)

        if node is None:
            node = ""
        elif isinstance(node, tuple):
            node = ".".join(node)

        return cls.from_str(f"{path}:{node}")
