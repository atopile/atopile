from faebryk.core.zig.gen.graph.graph import BoundNode, GraphView

class Linker:
    @staticmethod
    def link_type_reference(
        *,
        g: GraphView,
        type_reference: BoundNode,
        target_type_node: BoundNode,
    ) -> None: ...
