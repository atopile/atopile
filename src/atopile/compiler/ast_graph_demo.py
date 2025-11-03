from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import typer

import atopile.compiler.ast_types as AST
import faebryk.core.node as fabll
from atopile.compiler.ast_graph import Linker, build_file, build_stdlib
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


def describe_node(
    ctx: RenderNodeContext,
    *,
    include_parameter_literal: bool = False,
) -> str:
    bound = fabll.Node.bind_instance(ctx.node)
    type_name = bound.get_type_name() or "<anonymous>"

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
    edge_label = (
        EdgeComposition.get_name(edge=ctx.inbound_edge.edge())
        if ctx.inbound_edge
        else None
    ) or "<anonymous>"

    type_description = describe_node(ctx, include_parameter_literal=True)

    return f".{edge_label}: {type_description}"


def typegraph_renderer(ctx: RenderNodeContext) -> str:
    edge_name = (
        EdgeComposition.get_name(edge=ctx.inbound_edge.edge())
        if ctx.inbound_edge
        else None
    )
    edge_label = f".{edge_name}" if edge_name else "<anonymous>"

    type_description = describe_node(ctx, include_parameter_literal=True)

    return f"{edge_label}: {type_description}"


def instancegraph_renderer(ctx: RenderNodeContext, root: fabll.Node) -> str:
    edge_label = (
        EdgeComposition.get_name(edge=ctx.inbound_edge.edge())
        if ctx.inbound_edge
        else None
    ) or "<anonymous>"

    interface_edges: list[BoundEdge] = []
    ctx.node.visit_edges_of_type(
        edge_type=EdgeInterfaceConnection.get_tid(),
        ctx=interface_edges,
        f=lambda acc, bound_edge: acc.append(bound_edge),
    )

    extras = []
    for bound_edge in interface_edges:
        if bound_edge.edge().source().is_same(other=ctx.node.node()):
            partner_ref = bound_edge.edge().target()
        elif bound_edge.edge().target().is_same(other=ctx.node.node()):
            partner_ref = bound_edge.edge().source()
        else:
            continue

        partner_node = fabll.Node.bind_instance(bound_edge.g().bind(node=partner_ref))
        # TODO: also directed
        extras.append(f"~ {partner_node.relative_address(root=root)}")

    extras_text = " (" + ", ".join(extras) + ")" if extras else ""

    type_description = describe_node(ctx, include_parameter_literal=True)

    return f".{edge_label}: {type_description}{extras_text}"


def print_tree(
    bound_node: BoundNode,
    *,
    renderer: Callable[[RenderNodeContext], str],
    edge_types: Sequence[type] = (EdgeComposition,),
    exclude_node_types: Sequence[type] | None = None,
) -> None:
    edge_type_ids: list[int] = []
    for edge_type_cls in edge_types:
        get_tid = getattr(edge_type_cls, "get_tid", None)
        if not callable(get_tid):
            raise AttributeError(f"{edge_type_cls!r} must expose a callable get_tid()")
        edge_type_ids.append(get_tid())

    exclude_types = frozenset([t.__qualname__ for t in exclude_node_types or ()])

    root_type = fabll.Node.bind_instance(bound_node).get_type_name()
    if exclude_types and root_type is not None and root_type in exclude_types:
        return

    def gather_children(ctx: RenderNodeContext) -> list[RenderNodeContext]:
        children: list[RenderNodeContext] = []

        def add_child(acc: list[RenderNodeContext], bound_edge: BoundEdge) -> None:
            edge = bound_edge.edge()
            if not edge.source().is_same(other=ctx.node.node()):
                return

            child_node = ctx.node.g().bind(node=edge.target())
            child_type = fabll.Node.bind_instance(child_node).get_type_name()
            if exclude_types and child_type is not None and child_type in exclude_types:
                return

            if child_type == "Optional":
                optional_bound = fabll.Optional.bind_instance(child_node)
                value_node = optional_bound.get_value()
                if value_node is None:
                    raise ValueError(
                        "Optional node without value encountered during rendering"
                    )
                value_bound = value_node.instance
                value_type = fabll.Node.bind_instance(value_bound).get_type_name()
                if (
                    exclude_types
                    and value_type is not None
                    and value_type in exclude_types
                ):
                    return

                acc.append(
                    RenderNodeContext(
                        inbound_edge=bound_edge,
                        node=value_bound,
                        from_optional=True,
                    )
                )
                return

            acc.append(
                RenderNodeContext(
                    inbound_edge=bound_edge,
                    node=child_node,
                    from_optional=False,
                )
            )

        for edge_type_id in edge_type_ids:
            ctx.node.visit_edges_of_type(
                edge_type=edge_type_id,
                ctx=children,
                f=add_child,
            )

        return children

    def traverse(
        ctx: RenderNodeContext,
        ancestors: list,
        prefix: str,
        is_last: bool,
    ) -> None:
        label = renderer(ctx)
        if prefix:
            branch = "└─ " if is_last else "├─ "
            print(f"{prefix}{branch}{label}")
        else:
            print(label)

        next_prefix = prefix + ("   " if is_last else "│  ")
        next_ancestors = list(ancestors)

        current_node = ctx.node.node()
        if any(ancestor.is_same(other=current_node) for ancestor in ancestors):
            return

        next_ancestors.append(current_node)

        children = gather_children(ctx)
        for index, child_ctx in enumerate(children):
            traverse(
                child_ctx,
                next_ancestors,
                next_prefix,
                index == len(children) - 1,
            )

    root_ctx = RenderNodeContext(
        inbound_edge=None,
        node=bound_node,
        from_optional=False,
    )
    traverse(root_ctx, [], "", True)


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

    for i, (type_name, type_root) in enumerate(result.state.type_roots.items()):
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
