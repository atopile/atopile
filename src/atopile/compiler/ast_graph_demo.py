from pathlib import Path
from typing import cast

import atopile.compiler.ast_types as AST
from atopile.compiler.ast_graph import build_file
from atopile.compiler.graph_mock import BoundNode, NodeHelpers
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.source import EdgeSource
from faebryk.core.zig.gen.graph.graph import BoundEdge

RENDER_SOURCE_CHUNKS = False


def truncate_text(text: str) -> str:
    if "\n" in text:
        return text.split("\n")[0] + "..."
    return text


def ast_renderer(inbound_edge: BoundEdge | None, node: BoundNode) -> str:
    inbound_edge_name = (
        EdgeComposition.get_name(edge=inbound_edge.edge()) if inbound_edge else None
    ) or "<anonymous>"

    type_name = NodeHelpers.get_type_name(node)

    attrs = node.node().get_attrs()
    attrs.pop("uuid")
    attrs_text = (
        "<"
        + ", ".join([f"{k}={truncate_text(str(v))}" for k, v in attrs.items()])
        + ">"
        if attrs
        else ""
    )

    if type_name == "Parameter":
        lit_value = AST.try_extract_constrained_literal(node)
        match lit_value:
            case str():
                param_value = f" is! '{truncate_text(lit_value)}'"
            case _:
                param_value = f" is! {lit_value}"
    else:
        param_value = ""

    edge_text = f".{inbound_edge_name}: "

    return f"{edge_text}{type_name}{attrs_text}{param_value}"


def typegraph_renderer(n: BoundNode) -> str:
    attrs = n.node().get_attrs()
    attrs_text = [f"{k}={truncate_text(str(v))}" for k, v in attrs.items()]
    type_name = attrs.get("type_identifier")

    return f"{type_name}({', '.join(attrs_text)})"


if __name__ == "__main__":
    ast_root, type_graph = build_file(Path("examples/esp32_minimal/esp32_minimal.ato"))

    NodeHelpers.print_tree(
        ast_root,
        edge_types=[EdgeSource, EdgeComposition],
        renderer=ast_renderer,
        exclude_node_types=[AST.SourceChunk.__qualname__]
        if not RENDER_SOURCE_CHUNKS
        else None,
    )

    # NodeHelpers.print_tree(type_nodes["File"], renderer=typegraph_renderer)
