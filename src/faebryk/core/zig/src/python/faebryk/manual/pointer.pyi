from typing import Callable

from faebryk.core.faebrykpy import EdgeTraversal
from faebryk.core.zig.gen.faebryk.edgebuilder import EdgeCreationAttributes
from faebryk.core.zig.gen.graph.graph import (
    BoundEdge,
    BoundNode,
    EdgeReference,
    NodeReference,
)

class EdgePointer:
    @staticmethod
    def create(
        *,
        from_node: NodeReference,
        to_node: NodeReference,
        identifier: str | None = None,
    ) -> EdgeReference: ...
    @staticmethod
    def build(
        *, identifier: str | None, index: int | None
    ) -> EdgeCreationAttributes: ...
    @staticmethod
    def get_index(*, edge: EdgeReference) -> int | None: ...
    @staticmethod
    def is_instance(*, edge: EdgeReference) -> bool: ...
    @staticmethod
    def get_referenced_node(*, edge: EdgeReference) -> NodeReference: ...
    @staticmethod
    def get_referenced_node_from_node(*, node: BoundNode) -> BoundNode | None: ...
    @staticmethod
    def get_tid() -> EdgeReference.Type: ...
    @staticmethod
    def visit_pointed_edges[T](
        *, bound_node: BoundNode, ctx: T, f: Callable[[T, BoundEdge], None]
    ) -> None: ...
    @staticmethod
    def visit_pointed_edges_with_identifier[T](
        *,
        bound_node: BoundNode,
        identifier: str,
        ctx: T,
        f: Callable[[T, BoundEdge], None],
    ) -> None: ...
    @staticmethod
    def get_pointed_node_by_identifier(
        *, bound_node: BoundNode, identifier: str
    ) -> BoundNode | None: ...
    @staticmethod
    def point_to(
        *,
        bound_node: BoundNode,
        target_node: NodeReference,
        identifier: str | None = None,
        index: int | None,
    ) -> BoundEdge: ...
    @staticmethod
    def traverse() -> EdgeTraversal:
        """Create an EdgeTraversal for dereferencing the current Pointer node."""
        ...
