from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import typer

import atopile.compiler.ast_types as AST
import faebryk.core.node as fabll
from atopile.compiler.build import Linker, build_file, build_stdlib
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, GraphView

RENDER_SOURCE_CHUNKS = False


def truncate_text(text: str) -> str:
    if "\n" in text:
        return text.split("\n")[0] + "..."
    return text


@dataclass
class RenderNodeContext:
    inbound_edge: BoundEdge | None
    node: BoundNode
    from_optional: bool


def _type_name(node: BoundNode) -> str | None:
    try:
        return fabll.Node.bind_instance(node).get_type_name()
    except Exception:
        return None


def _format_edge_label(
    edge: BoundEdge | None,
    *,
    prefix_on_name: bool = True,
    prefix_on_anonymous: bool = True,
) -> str:
    edge_name = EdgeComposition.get_name(edge=edge.edge()) if edge else None
    if edge_name:
        return f".{edge_name}" if prefix_on_name else edge_name
    return ".<anonymous>" if prefix_on_anonymous else "<anonymous>"


def _flatten_optional(node: BoundNode) -> tuple[BoundNode, bool]:
    current = node
    from_optional = False

    while _type_name(current) == "Optional":
        optional_bound = fabll.Optional.bind_instance(current)
        value_node = optional_bound.get_value()
        if value_node is None:
            raise ValueError("Optional node without value encountered during rendering")
        current = value_node.instance
        from_optional = True

    return current, from_optional


def _collect_interface_extras(node: BoundNode, root: fabll.Node) -> str:
    interface_edges: list[BoundEdge] = []
    node.visit_edges_of_type(
        edge_type=EdgeInterfaceConnection.get_tid(),
        ctx=interface_edges,
        f=lambda acc, bound_edge: acc.append(bound_edge),
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
        extras.append(f"~ {partner_node.relative_address(root=root)}")

    return " (" + ", ".join(extras) + ")" if extras else ""


def _edge_type_ids(edge_types: Sequence[type]) -> list[int]:
    ids: list[int] = []
    for edge_type_cls in edge_types:
        get_tid = getattr(edge_type_cls, "get_tid", None)
        if not callable(get_tid):
            raise AttributeError(f"{edge_type_cls!r} must expose a callable get_tid()")
        ids.append(get_tid())
    return ids


def _excluded_names(exclude_node_types: Sequence[type] | None) -> frozenset[str]:
    if not exclude_node_types:
        return frozenset()
    return frozenset(t.__qualname__ for t in exclude_node_types)


def _is_excluded(node: BoundNode, excluded: frozenset[str]) -> bool:
    if not excluded:
        return False
    type_name = _type_name(node)
    return type_name is not None and type_name in excluded


def _child_contexts(
    parent: BoundNode,
    *,
    edge_type_ids: Sequence[int],
    excluded: frozenset[str],
) -> list[RenderNodeContext]:
    children: list[RenderNodeContext] = []

    def add_child(acc: list[RenderNodeContext], bound_edge: BoundEdge) -> None:
        edge = bound_edge.edge()
        if not edge.source().is_same(other=parent.node()):
            return

        child_node = parent.g().bind(node=edge.target())
        flattened_node, from_optional = _flatten_optional(child_node)
        if _is_excluded(flattened_node, excluded):
            return

        acc.append(
            RenderNodeContext(
                inbound_edge=bound_edge,
                node=flattened_node,
                from_optional=from_optional,
            )
        )

    for edge_type_id in edge_type_ids:
        parent.visit_edges_of_type(
            edge_type=edge_type_id,
            ctx=children,
            f=add_child,
        )

    return children


def describe_node(
    ctx: RenderNodeContext,
    *,
    include_parameter_literal: bool = False,
) -> str:
    type_name = _type_name(ctx.node) or "<anonymous>"

    attrs = ctx.node.node().get_attrs()
    attrs_parts = [
        f"{k}={truncate_text(str(v))}" for k, v in attrs.items() if k != "uuid"
    ]
    attrs_text = f"<{', '.join(attrs_parts)}>" if attrs_parts else ""

    result = f"{type_name}{attrs_text}"

    if include_parameter_literal and type_name == "Parameter":
        match fabll.Parameter.bind_instance(ctx.node).try_extract_constrained_literal():
            case str() as lit_value:
                result += f" is! '{truncate_text(lit_value)}'"
            case None:
                pass
            case lit_value:
                result += f" is! {lit_value}"

    return f"?{result}" if ctx.from_optional else result


def ast_renderer(ctx: RenderNodeContext) -> str:
    edge_label = _format_edge_label(ctx.inbound_edge)
    type_description = describe_node(ctx, include_parameter_literal=True)
    return f"{edge_label}: {type_description}"


def typegraph_renderer(ctx: RenderNodeContext) -> str:
    edge_label = _format_edge_label(ctx.inbound_edge, prefix_on_anonymous=False)
    type_description = describe_node(ctx, include_parameter_literal=True)
    return f"{edge_label}: {type_description}"


def instancegraph_renderer(ctx: RenderNodeContext, root: fabll.Node) -> str:
    edge_label = _format_edge_label(ctx.inbound_edge)
    type_description = describe_node(ctx, include_parameter_literal=True)
    extras_text = _collect_interface_extras(ctx.node, root)
    return f"{edge_label}: {type_description}{extras_text}"


def print_tree(
    bound_node: BoundNode,
    *,
    renderer: Callable[[RenderNodeContext], str],
    edge_types: Sequence[type] = (EdgeComposition,),
    exclude_node_types: Sequence[type] | None = None,
) -> None:
    edge_type_ids = _edge_type_ids(edge_types)
    excluded = _excluded_names(exclude_node_types)

    root_node, root_from_optional = _flatten_optional(bound_node)
    if _is_excluded(root_node, excluded):
        return

    visited: set[int] = set()

    def walk(ctx: RenderNodeContext, prefix: str, is_last: bool) -> None:
        line = renderer(ctx)
        if prefix:
            connector = "└─ " if is_last else "├─ "
            print(f"{prefix}{connector}{line}")
        else:
            print(line)

        node_uuid = ctx.node.node().get_uuid()
        if node_uuid in visited:
            return

        visited.add(node_uuid)

        child_prefix = prefix + ("   " if is_last else "│  ")
        children = _child_contexts(
            ctx.node, edge_type_ids=edge_type_ids, excluded=excluded
        )
        for index, child_ctx in enumerate(children):
            walk(child_ctx, child_prefix, index == len(children) - 1)

        visited.remove(node_uuid)

    root_ctx = RenderNodeContext(
        inbound_edge=None,
        node=root_node,
        from_optional=root_from_optional,
    )
    walk(root_ctx, prefix="", is_last=True)


def main():
    source_path = Path("examples/esp32_minimal/esp32_minimal.ato")

    def _section(title: str, sep: str = "\n"):
        print(sep + f" {title} ".center(80, "="))

    _section("Build logs", sep="")
    graph = GraphView.create()

    stdlib_tg, stdlib_registry = build_stdlib(graph)

    result = build_file(graph, source_path.resolve())

    _section("AST Graph")
    print_tree(
        result.ast_root.instance,
        renderer=ast_renderer,
        exclude_node_types=[AST.SourceChunk] if not RENDER_SOURCE_CHUNKS else None,
    )

    for type_name, type_root in result.state.type_roots.items():
        _section(f"Pre-Link Type Graph {type_name}")
        print_tree(type_root, renderer=typegraph_renderer)

    _section("Linking", sep="\n\n")
    Linker.link_imports(graph, result.state, stdlib_registry, stdlib_tg)

    _section("Post-Link Type Graph: ESP32_MINIMAL")
    app_type = result.state.type_roots["ESP32_MINIMAL"]
    print_tree(app_type, renderer=typegraph_renderer)

    _section("Instance Graph")
    app = result.state.type_graph.instantiate_node(type_node=app_type, attributes={})
    print_tree(
        app,
        renderer=lambda ctx: instancegraph_renderer(
            ctx, root=fabll.Node.bind_instance(app)
        ),
    )


app = typer.Typer(rich_markup_mode="rich")
app.command()(main)
app()
