from faebryk.core.zig.gen.graph.graph import Edge, Literal

class EdgeCreationAttributes:
    def __init__(
        self,
        *,
        edge_type: int,
        directional: bool | None,
        name: str | None,
        dynamic: dict[str, Literal] | None,
    ) -> None: ...
    def apply_to(self, *, edge: Edge) -> None: ...
