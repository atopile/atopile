from typing import Callable

from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, Edge, Node

class EdgeComposition:
    @staticmethod
    def create(*, parent: Node, child: Node, child_identifier: str) -> Edge: ...
    @staticmethod
    def is_instance(*, edge: Edge) -> bool: ...
    @staticmethod
    def visit_children_edges[T](
        *,
        bound_node: BoundNode,
        ctx: T,
        f: Callable[[T, BoundEdge], None],
    ) -> None: ...
    @staticmethod
    def get_parent_edge(*, bound_node: BoundNode) -> BoundEdge | None: ...
    @staticmethod
    def add_child(
        *, bound_node: BoundNode, child: Node, child_identifier: str
    ) -> BoundEdge: ...
    @staticmethod
    def get_name(*, edge: Edge) -> str: ...
    @staticmethod
    def get_tid() -> Edge.Type: ...
    @staticmethod
    def get_child_by_identifier(
        *, bound_node: BoundNode, child_identifier: str
    ) -> BoundNode | None: ...
