from pathlib import Path

import atopile.compiler.ast_types as AST
import faebryk.core.node as fabll
from atopile.compiler.ast_graph import build_file, build_stdlib, link_imports
from atopile.compiler.graph_mock import BoundNode, NodeHelpers
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.graph.graph import BoundEdge, GraphView

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
    edge_name = (
        EdgeComposition.get_name(edge=inbound_edge.edge()) if inbound_edge else None
    )
    edge_label = f".{edge_name}" if edge_name else "<anonymous>"

    type_name = fabll.Node.bind_instance(node).get_type_name()

    attrs = node.node().get_attrs()
    attrs_parts = [
        f"{k}={truncate_text(str(v))}" for k, v in attrs.items() if k != "uuid"
    ]
    attrs_text = f"<{', '.join(attrs_parts)}>" if attrs_parts else ""

    return f"{edge_label}: {type_name}{attrs_text}"


def instancegraph_renderer(
    inbound_edge: BoundEdge | None, node: BoundNode, root: fabll.Node
) -> str:
    edge_label = (
        EdgeComposition.get_name(edge=inbound_edge.edge()) if inbound_edge else None
    ) or "<anonymous>"

    type_name = fabll.Node.bind_instance(node).get_type_name()

    interface_edges: list[BoundEdge] = []
    node.visit_edges_of_type(
        edge_type=EdgeInterfaceConnection.get_tid(),
        ctx=interface_edges,
        f=lambda ctx, bound_edge: ctx.append(bound_edge),
    )

    extras = []
    for bound_edge in interface_edges:
        if bound_edge.edge().source().is_same(other=node.node()):
            partner_ref = bound_edge.edge().target()
        elif bound_edge.edge().target().is_same(other=node.node()):
            partner_ref = bound_edge.edge().source()
        else:
            continue

        partner_node = fabll.Node.bind_instance(bound_edge.g().bind(node=partner_ref))
        # TODO: also directed
        extras.append(f"~ {partner_node.relative_address(root=root)}")

    extras_text = " (" + ", ".join(extras) + ")" if extras else ""

    return f".{edge_label}: {type_name}{extras_text}"


if __name__ == "__main__":
    source_path = Path("examples/esp32_minimal/esp32_minimal.ato")

    def _section(title: str, sep: str = "\n"):
        print(sep + f" {title} ".center(80, "="))

    _section("Build logs", sep="")
    graph = GraphView.create()

    stdlib_tg, stdlib_registry = build_stdlib(graph)

    result = build_file(graph, source_path.resolve())

    _section("AST Graph")
    NodeHelpers.print_tree(
        result.ast_root.instance,
        renderer=ast_renderer,
        exclude_node_types=[AST.SourceChunk] if not RENDER_SOURCE_CHUNKS else None,
    )

    for i, (type_name, type_root) in enumerate(result.state.type_roots.items()):
        _section(f"Pre-Link Type Graph {type_name}")
        NodeHelpers.print_tree(type_root, renderer=typegraph_renderer)

    _section("Linking", sep="\n\n")
    link_imports(graph, result.state, stdlib_registry, stdlib_tg)

    _section("Post-Link Type Graph: ESP32_MINIMAL")
    app_type = result.state.type_roots["ESP32_MINIMAL"]
    NodeHelpers.print_tree(app_type, renderer=typegraph_renderer)

    _section("Instance Graph")
    app = result.state.type_graph.instantiate_node(type_node=app_type, attributes={})
    NodeHelpers.print_tree(
        app,
        renderer=lambda inbound_edge, node: instancegraph_renderer(
            inbound_edge, node, root=fabll.Node.bind_instance(app)
        ),
    )
