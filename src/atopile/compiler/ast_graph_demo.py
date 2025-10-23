from pathlib import Path

import atopile.compiler.ast_types as AST
import faebryk.core.node as fabll
from atopile.compiler.ast_graph import build_file
from atopile.compiler.graph_mock import BoundNode, NodeHelpers
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.graph.graph import BoundEdge

RENDER_SOURCE_CHUNKS = False


def truncate_text(text: str) -> str:
    if "\n" in text:
        return text.split("\n")[0] + "..."
    return text


def ast_renderer(inbound_edge: BoundEdge | None, node: BoundNode) -> str:
    edge_label = (
        EdgeComposition.get_name(edge=inbound_edge.edge()) if inbound_edge else None
    ) or "<anonymous>"

    type_name = fabll.Node.bind_instance(node).get_type_name()

    attrs = node.node().get_attrs()
    attrs_parts = [
        f"{k}={truncate_text(str(v))}" for k, v in attrs.items() if k != "uuid"
    ]
    attrs_text = f"<{', '.join(attrs_parts)}>" if attrs_parts else ""

    param_value = ""
    if type_name == "Parameter":
        match lit_value := fabll.Parameter.bind_instance(
            node
        ).try_extract_constrained_literal():
            case str():
                param_value = f" is! '{truncate_text(lit_value)}'"
            case _:
                param_value = f" is! {lit_value}"

    return f".{edge_label}: {type_name}{attrs_text}{param_value}"


def typegraph_renderer(inbound_edge: BoundEdge | None, node: BoundNode) -> str:
    edge_label = (
        EdgeComposition.get_name(edge=inbound_edge.edge()) if inbound_edge else None
    ) or "<anonymous>"

    type_name = fabll.Node.bind_instance(node).get_type_name()

    attrs = node.node().get_attrs()
    attrs_parts = [
        f"{k}={truncate_text(str(v))}" for k, v in attrs.items() if k != "uuid"
    ]
    attrs_text = f"<{', '.join(attrs_parts)}>" if attrs_parts else ""

    return f".{edge_label}: {type_name}{attrs_text}"


def instancegraph_renderer(inbound_edge: BoundEdge | None, node: BoundNode) -> str:
    edge_label = (
        EdgeComposition.get_name(edge=inbound_edge.edge()) if inbound_edge else None
    ) or "<anonymous>"

    type_name = fabll.Node.bind_instance(node).get_type_name()
    return f".{edge_label}: {type_name}"


if __name__ == "__main__":

    def _section(title: str, sep: str = "\n"):
        print(sep + f" {title} ".center(80, "="))

    _section("Build logs", sep="")
    type_graph, ast_root, type_roots = build_file(
        Path("examples/esp32_minimal/esp32_minimal.ato")
    )

    _section("AST Graph")
    NodeHelpers.print_tree(
        ast_root.instance,
        renderer=ast_renderer,
        exclude_node_types=[AST.SourceChunk] if not RENDER_SOURCE_CHUNKS else None,
    )

    for i, type_root in enumerate(type_roots):
        _section(f"Type Graph {i + 1}")

        NodeHelpers.print_tree(type_root, renderer=typegraph_renderer)

    app_type = next(
        n
        for n in type_roots
        if n.node().get_attr(key="type_identifier") == "ESP32_MINIMAL"
    )

    app = type_graph.instantiate_node(type_node=app_type, attributes={})

    _section("Instance Graph")
    NodeHelpers.print_tree(app, renderer=instancegraph_renderer)
