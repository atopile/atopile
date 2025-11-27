from typing import Callable

from faebryk.core.zig.gen.faebryk.edgebuilder import EdgeCreationAttributes
from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, Edge, Node

class Trait:
    @staticmethod
    def add_trait_to(*, target: BoundNode, trait_type: BoundNode) -> BoundNode: ...
    @staticmethod
    def mark_as_trait(*, trait_type: BoundNode) -> None: ...
    @staticmethod
    def try_get_trait(
        *, target: BoundNode, trait_type: BoundNode
    ) -> BoundNode | None: ...
    @staticmethod
    def visit_implementers[T](
        *, trait_type: BoundNode, ctx: T, f: Callable[[T, BoundNode], None]
    ) -> None: ...

class EdgeTrait:
    @staticmethod
    def create(*, owner_node: Node, trait_instance: Node) -> Edge: ...
    @staticmethod
    def build() -> EdgeCreationAttributes: ...
    @staticmethod
    def is_instance(*, edge: Edge) -> bool: ...
    @staticmethod
    def get_owner_node(*, edge: Edge) -> Node: ...
    @staticmethod
    def get_trait_instance_node(*, edge: Edge) -> Node: ...
    @staticmethod
    def get_trait_instance_of(*, edge: Edge, node: Node) -> Node | None: ...
    @staticmethod
    def get_owner_of(*, edge: Edge, node: Node) -> Node | None: ...
    @staticmethod
    def visit_trait_instance_edges[T](
        *, bound_node: BoundNode, ctx: T, f: Callable[[T, BoundEdge], None]
    ) -> None: ...
    @staticmethod
    def get_owner_edge(*, bound_node: BoundNode) -> BoundEdge | None: ...
    @staticmethod
    def get_owner_node_of(*, bound_node: BoundNode) -> BoundNode | None: ...
    @staticmethod
    def add_trait_instance(
        *, bound_node: BoundNode, trait_instance: Node
    ) -> BoundEdge: ...
    @staticmethod
    def visit_trait_instances_of_type[T](
        *,
        owner: BoundNode,
        trait_type: Node,
        ctx: T,
        f: Callable[[T, BoundEdge], None],
    ) -> None: ...
    @staticmethod
    def try_get_trait_instance_of_type(
        *, bound_node: BoundNode, trait_type: Node
    ) -> BoundNode | None: ...
