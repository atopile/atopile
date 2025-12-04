from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import typer

import atopile.compiler.ast_types as AST
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.compiler.build import Linker, build_file, build_stdlib
from atopile.config import config
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, GraphView

RENDER_SOURCE_CHUNKS = False
MAX_VALUE_LENGTH = 40


def truncate_text(text: str, max_length: int = MAX_VALUE_LENGTH) -> str:
    if "\n" in text:
        text = text.split("\n")[0] + "..."
    if len(text) > max_length:
        return text[: max_length - 3] + "..."
    return text


@dataclass
class RenderNodeContext:
    inbound_edge: BoundEdge | None
    node: BoundNode


def _type_name(node: BoundNode) -> str | None:
    return fabll.Node.bind_instance(node).get_type_name()


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
        if _is_excluded(child_node, excluded):
            return

        acc.append(RenderNodeContext(inbound_edge=bound_edge, node=child_node))

    for edge_type_id in edge_type_ids:
        parent.visit_edges_of_type(
            edge_type=edge_type_id,
            ctx=children,
            f=add_child,
        )

    return children


def _format_list(values: list, max_items: int = 3, quote: str = "") -> str:
    """Format a list of values for display."""
    formatted = ", ".join(f"{quote}{v}{quote}" for v in values[:max_items])
    suffix = "..." if len(values) > max_items else ""
    return f"[{formatted}{suffix}]"


def _extract_literal_value(node: BoundNode, type_name: str) -> str | None:
    """Extract display value from literal types."""
    try:
        match type_name:
            # Collection types
            case "Strings":
                values = F.Literals.Strings.bind_instance(node).get_values()
                if len(values) == 1:
                    return f'"{truncate_text(values[0])}"'
                elif values:
                    return _format_list(
                        [truncate_text(v) for v in values], max_items=3, quote='"'
                    )
            case "Counts":
                values = F.Literals.Counts.bind_instance(node).get_values()
                if len(values) == 1:
                    return str(values[0])
                elif values:
                    return _format_list(values, max_items=5)
            case "Booleans":
                values = F.Literals.Booleans.bind_instance(node).get_values()
                if len(values) == 1:
                    return str(values[0])
                elif values:
                    return _format_list(values)
            case "Numerics":
                values = list(F.Literals.Numerics.bind_instance(node).get_values())
                if len(values) == 1:
                    return str(values[0])
                elif values:
                    return _format_list(values)
            # Tagged union
            case "AnyLiteral":
                value = F.Literals.AnyLiteral.bind_instance(node).get_value()
                if isinstance(value, str):
                    return f'"{truncate_text(value)}"'
                return str(value)
            # Enums
            case _ if type_name.endswith("Enums") or type_name == "AbstractEnums":
                bound = F.Literals.AbstractEnums.bind_instance(node)
                values = bound.get_values()
                if len(values) == 1:
                    return f"'{values[0]}'"
                elif values:
                    return _format_list(values, quote="'")
            # AST location info
            case "FileLocation":
                loc = AST.FileLocation.bind_instance(node)
                start = f"{loc.get_start_line()}:{loc.get_start_col()}"
                end = f"{loc.get_end_line()}:{loc.get_end_col()}"
                return f"{start}-{end}"
    except Exception:
        pass
    return None


def describe_node(
    ctx: RenderNodeContext,
    *,
    include_literal_values: bool = False,
) -> str:
    type_name = _type_name(ctx.node) or "<anonymous>"

    attrs = ctx.node.node().get_attrs()
    attrs_parts = [
        f"{k}={truncate_text(str(v))}" for k, v in attrs.items() if k != "uuid"
    ]
    attrs_text = f"<{', '.join(attrs_parts)}>" if attrs_parts else ""

    result = f"{type_name}{attrs_text}"

    if include_literal_values:
        literal_value = _extract_literal_value(ctx.node, type_name)
        if literal_value:
            result += f" = {literal_value}"

    return result


def ast_renderer(ctx: RenderNodeContext) -> str:
    edge_label = _format_edge_label(ctx.inbound_edge)
    type_description = describe_node(ctx, include_literal_values=True)
    return f"{edge_label}: {type_description}"


def typegraph_renderer(ctx: RenderNodeContext) -> str:
    edge_label = _format_edge_label(ctx.inbound_edge, prefix_on_anonymous=False)
    type_description = describe_node(ctx, include_literal_values=True)
    return f"{edge_label}: {type_description}"


def instancegraph_renderer(ctx: RenderNodeContext, root: fabll.Node) -> str:
    edge_label = _format_edge_label(ctx.inbound_edge)
    type_description = describe_node(ctx, include_literal_values=True)
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

    root_node = bound_node
    if _is_excluded(root_node, excluded):
        return

    visited: set[int] = set()

    def walk(ctx: RenderNodeContext, prefix: str, is_last: bool) -> None:
        node_uuid = ctx.node.node().get_uuid()
        is_cycle = node_uuid in visited

        line = renderer(ctx)
        if is_cycle:
            line += " ↺"  # cycle indicator

        if prefix:
            connector = "└─ " if is_last else "├─ "
            print(f"{prefix}{connector}{line}")
        else:
            print(line)

        if is_cycle:
            return

        visited.add(node_uuid)

        child_prefix = prefix + ("   " if is_last else "│  ")
        children = _child_contexts(
            ctx.node, edge_type_ids=edge_type_ids, excluded=excluded
        )
        for index, child_ctx in enumerate(children):
            walk(child_ctx, child_prefix, index == len(children) - 1)

        visited.remove(node_uuid)

    root_ctx = RenderNodeContext(inbound_edge=None, node=root_node)
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
    excluded_types: list[type] = []
    if not RENDER_SOURCE_CHUNKS:
        excluded_types.append(AST.SourceChunk)
    print_tree(
        result.ast_root.instance,
        renderer=ast_renderer,
        exclude_node_types=excluded_types or None,
    )

    for type_name, type_root in result.state.type_roots.items():
        _section(f"Pre-Link Type Graph {type_name}")
        print_tree(type_root, renderer=typegraph_renderer)

    _section("Linking", sep="\n\n")
    linker = Linker(config, stdlib_registry, stdlib_tg)
    linker.link_imports(graph, result.state)

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
