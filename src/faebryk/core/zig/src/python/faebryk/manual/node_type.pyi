from typing import Callable

from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, Edge, Node

class EdgeType:
    @staticmethod
    def create(*, type_node: Node, instance_node: Node, edge_name: str) -> Edge: ...
    @staticmethod
    def is_instance(*, edge: Edge) -> bool: ...
    @staticmethod
    def visit_instance_edges[T](
        *,
        bound_node: BoundNode,
        ctx: T,
        f: Callable[[T, BoundEdge], None],
    ) -> None: ...
    @staticmethod
    def get_type_node(*, edge: Edge) -> Node: ...
    @staticmethod
    def get_instance_node(*, edge: Edge) -> Node | None: ...
    @staticmethod
    def get_type_edge(*, bound_node: BoundNode) -> BoundEdge | None: ...
    @staticmethod
    def add_instance(
        *,
        bound_type_node: BoundNode,
        bound_instance_node: BoundNode,
        instance_identifier: str,
    ) -> BoundEdge: ...
    @staticmethod
    def get_name(*, edge: Edge) -> str: ...
    @staticmethod
    def get_tid() -> Edge.Type: ...
    @staticmethod
    def is_node_instance_of(*, bound_node: BoundNode, node_type: Node) -> bool: ...
