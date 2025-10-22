from typing import Callable

from faebryk.core.zig.gen.faebryk.edgebuilder import EdgeCreationAttributes
from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, Edge, Node

class EdgePointer:
    @staticmethod
    def create(
        *, from_node: Node, to_node: Node, identifier: str | None = None
    ) -> Edge: ...
    @staticmethod
    def build(*, identifier: str | None) -> EdgeCreationAttributes: ...
    @staticmethod
    def is_instance(*, edge: Edge) -> bool: ...
    @staticmethod
    def get_referenced_node(*, edge: Edge) -> Node | None: ...
    @staticmethod
    def get_referenced_node_from_node(*, node: BoundNode) -> BoundNode | None: ...
    @staticmethod
    def get_tid() -> Edge.Type: ...
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
        *, bound_node: BoundNode, target_node: Node, identifier: str | None = None
    ) -> BoundEdge: ...
