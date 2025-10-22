from typing import Callable

from faebryk.core.zig.gen.faebryk.edgebuilder import EdgeCreationAttributes
from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, Edge, Node

class EdgeComposition:
    @staticmethod
    def create(*, parent: Node, child: Node, child_identifier: str) -> Edge: ...
    @staticmethod
    def build(*, child_identifier: str) -> EdgeCreationAttributes: ...
    @staticmethod
    def is_instance(*, edge: Edge) -> bool: ...
    @staticmethod
    def get_parent_node(*, edge: Edge) -> Node: ...
    @staticmethod
    def get_child_node(*, edge: Edge) -> Node: ...
    @staticmethod
    def get_child_of(*, edge: Edge, node: Node) -> Node | None: ...
    @staticmethod
    def get_parent_of(*, edge: Edge, node: Node) -> Node | None: ...
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
    def get_parent_node_of(*, bound_node: BoundNode) -> BoundNode | None: ...
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
        *, node: BoundNode, child_identifier: str
    ) -> BoundNode | None: ...
    @staticmethod
    def visit_children_of_type[T](
        *,
        bound_node: BoundNode,
        child_type: Node,
        ctx: T,
        f: Callable[[T, BoundEdge], None],
    ) -> None: ...
    @staticmethod
    def try_get_single_child_of_type(
        *, bound_node: BoundNode, child_type: Node
    ) -> BoundNode | None: ...
