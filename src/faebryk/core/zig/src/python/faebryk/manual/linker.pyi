from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundNode, GraphView

class Linker:
    @staticmethod
    def link_type_reference(
        *,
        g: GraphView,
        type_reference: BoundNode,
        target_type_node: BoundNode,
    ) -> None: ...
    @staticmethod
    def update_type_reference(
        *,
        g: GraphView,
        type_reference: BoundNode,
        target_type_node: BoundNode,
    ) -> None: ...
    @staticmethod
    def get_resolved_type(*, type_reference: BoundNode) -> BoundNode | None: ...
    @staticmethod
    def collect_unresolved_type_references(
        *,
        type_graph: TypeGraph,
    ) -> list[tuple[BoundNode, BoundNode]]: ...
