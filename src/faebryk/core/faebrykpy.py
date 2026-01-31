from dataclasses import dataclass
from typing import TYPE_CHECKING

from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.edgebuilder import EdgeCreationAttributes
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.faebryk.linker import Linker
from faebryk.core.zig.gen.faebryk.next import EdgeNext
from faebryk.core.zig.gen.faebryk.node_type import EdgeType
from faebryk.core.zig.gen.faebryk.nodebuilder import NodeCreationAttributes
from faebryk.core.zig.gen.faebryk.operand import EdgeOperand
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.core.zig.gen.faebryk.trait import EdgeTrait as _ZigEdgeTrait
from faebryk.core.zig.gen.faebryk.trait import Trait
from faebryk.core.zig.gen.faebryk.typegraph import (
    TypeGraph,
    TypeGraphInstantiationError,
    TypeGraphPathError,
    TypeGraphResolveError,
)

if TYPE_CHECKING:
    import faebryk.core.node as fabll


# Not really sure where this belongs, but it's here for now.
@dataclass
class EdgeTraversal:
    """Specifies how to traverse an edge in a reference path.

    Use the traverse() methods on the edge types to create these:
    - EdgeComposition.traverse(identifier="child_name")
    - EdgeTrait.traverse(trait_type=can_bridge)  # Type-safe
    - EdgePointer.traverse() - dereferences the current Pointer node

    Example:
        from faebryk.library.can_bridge import can_bridge
        from faebryk.core.faebrykpy import EdgeTrait

        tg.ensure_child_reference(type_node=t, path=[
            "resistor",                              # String defaults to Composition
            EdgeTrait.traverse(trait_type=can_bridge),
            EdgeComposition.traverse(identifier="out_"),
            EdgePointer.traverse(),                  # Dereference to target
        ])
    """

    identifier: str
    edge_type: int  # Edge type tid

    def __str__(self) -> str:
        """Return string representation suitable for use in identifiers."""
        return self.identifier


class _EdgeTraitMeta(type):
    """Metaclass that delegates attribute access to the Zig EdgeTrait,
    except for `traverse` which is overridden with type-safe version.
    """

    def __getattr__(cls, name: str):
        # Delegate all attribute access to Zig implementation
        return getattr(_ZigEdgeTrait, name)


class EdgeTrait(metaclass=_EdgeTraitMeta):
    """Wrapper for EdgeTrait with type-safe traverse() method.

    Provides a Python-friendly API that accepts trait types directly,
    extracting the type identifier automatically. All other methods
    are delegated to the Zig implementation.
    """

    @staticmethod
    def traverse(
        *,
        trait_type: "type[fabll.Node] | None" = None,
        trait_type_name: str | None = None,
    ) -> EdgeTraversal:
        """Create an EdgeTraversal for finding a trait instance.

        Args:
            trait_type: The trait class (e.g., can_bridge). Preferred for type safety.
            trait_type_name: The trait type name as a string. Fallback for dynamic use.

        Returns:
            EdgeTraversal configured for trait edge traversal.

        Raises:
            ValueError: If neither trait_type nor trait_type_name is provided.
        """
        if trait_type is not None:
            trait_type_name = trait_type._type_identifier()
        elif trait_type_name is None:
            raise ValueError("Either trait_type or trait_type_name must be provided")
        return _ZigEdgeTrait.traverse(trait_type_name=trait_type_name)


__all__ = [
    "EdgeComposition",
    "EdgeCreationAttributes",
    "EdgeInterfaceConnection",
    "EdgeNext",
    "EdgeOperand",
    "EdgePointer",
    "EdgeTrait",
    "EdgeTraversal",
    "EdgeType",
    "Linker",
    "NodeCreationAttributes",
    "Trait",
    "TypeGraph",
    "TypeGraphPathError",
    "TypeGraphInstantiationError",
    "TypeGraphResolveError",
]
