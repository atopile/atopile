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

        return cls(f"{path}:{node}")
