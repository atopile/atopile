# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
EdgeTraversal - specifies how to traverse edges in a reference path.

This is a pure Python class that complements the Zig typegraph bindings.
"""

from dataclasses import dataclass

import faebryk.core.faebrykpy as fbrk


@dataclass
class EdgeTraversal:
    """Specifies how to traverse an edge in a reference path.

    Use with ensure_child_reference() to traverse different edge types:
    - Composition edges (parent-child): Use string or EdgeTraversal.composition()
    - Trait edges: EdgeTraversal.trait("trait_name")
    - Pointer edges: EdgeTraversal.pointer("pointer_name")

    Example:
        # Mixed path with different edge types
        tg.ensure_child_reference(type_node=t, path=[
            "resistor",  # Composition (string default)
            EdgeTraversal.trait("can_bridge"),
            EdgeTraversal.pointer("in_"),
        ])
    """

    identifier: str
    edge_type: int  # Edge type tid

    @classmethod
    def composition(cls, identifier: str) -> "EdgeTraversal":
        """Create a Composition edge traversal (the default for strings)."""
        return cls(identifier, fbrk.EdgeComposition.get_tid())

    @classmethod
    def trait(cls, identifier: str) -> "EdgeTraversal":
        """Create a Trait edge traversal."""
        return cls(identifier, fbrk.EdgeTrait.get_tid())

    @classmethod
    def pointer(cls, identifier: str) -> "EdgeTraversal":
        """Create a Pointer edge traversal."""
        return cls(identifier, fbrk.EdgePointer.get_tid())
