from typing import Callable

from faebryk.core.zig.gen.faebryk.edgebuilder import EdgeCreationAttributes
from faebryk.core.zig.gen.graph.graph import BFSPath, BoundEdge, BoundNode, Edge, Node

class EdgeInterfaceConnection:
    @staticmethod
    def get_tid() -> Edge.Type: ...
    @staticmethod
    def is_instance(*, edge: Edge) -> bool: ...
    @staticmethod
    def get_other_connected_node(*, edge: Edge, node: Node) -> Node | None: ...
    @staticmethod
    def connect(*, bn1: BoundNode, bn2: BoundNode) -> BoundEdge: ...
    @staticmethod
    def connect_shallow(*, bn1: BoundNode, bn2: BoundNode) -> BoundEdge: ...
    @staticmethod
    def visit_connected_edges[T](
        *,
        bound_node: BoundNode,
        ctx: T,
        f: Callable[[T, BoundEdge], None],
    ) -> None: ...
    @staticmethod
    def is_connected_to(*, source: BoundNode, target: BoundNode) -> BFSPath: ...
    @staticmethod
    def get_connected(
        *, source: BoundNode, include_self: bool = True
    ) -> dict[BoundNode, BFSPath]: ...  # Returns dict mapping nodes to BFSPath objects
    @staticmethod
    def build(*, shallow: bool = ...) -> EdgeCreationAttributes: ...
