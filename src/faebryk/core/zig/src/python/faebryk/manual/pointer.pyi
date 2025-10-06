from faebryk.core.zig.gen.graph.graph import BoundNode, Edge, Node


class EdgePointer:
    @staticmethod
    def create(*, from_node: Node, to_node: Node, identifier: str) -> Edge: ...

    @staticmethod
    def is_instance(*, edge: Edge) -> bool: ...

    @staticmethod
    def get_referenced_node(*, edge: Edge) -> Node | None: ...

    @staticmethod
    def resolve_reference(*, reference_node: Node, base_node: BoundNode) -> Node | None: ...
