"""
Addresses are references to a specific node.
They take the form: "path/to/file.ato:node.path"
Addresses go by other names in various files for historical reasons - but should be upgraded.

This file provides utilities for working with addresses.
"""
from pathlib import Path
from os import PathLike
from typing import Optional


def get_file(address: str) -> Path:
    """
    Extract the file path from an address.
    """
    return Path(address.split(":")[0])


def get_node_str(address: str) -> str:
    """
    Extract the node path from an address.
    """
    return address.split(":")[1]


def get_node_as_ref(address: str) -> tuple[str]:
    """
    Extract the node path from an address.
    """
    return tuple(get_node_str(address).split("."))


class AddrValueError(ValueError):
    """
    Raised when an address is invalid.
    """


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
    else:
        return True


class AddrStr(str):
    """
    Thin wrapper class to represent specifically addresses.
    """

    @property
    def file(self) -> Path:
        return get_file(self)

    @property
    def node_as_str(self) -> str:
        return get_node_str(self)

    @property
    def node_as_ref(self) -> tuple[str]:
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
