#!/usr/bin/env python3
from pathlib import Path

import typer

import atopile.compiler.ast_types as AST
import faebryk.core.node as fabll
from atopile.compiler.build import Linker, build_file, build_stdlib
from atopile.config import config
from faebryk.core.node import TreeRenderer
from faebryk.core.zig.gen.graph.graph import BoundNode, GraphView


def extract_value(node: BoundNode, type_name: str) -> str | None:
    """Extract display value, handling compiler-specific AST types."""
    if type_name == "FileLocation":
        loc = AST.FileLocation.bind_instance(node)
        start = f"{loc.get_start_line()}:{loc.get_start_col()}"
        end = f"{loc.get_end_line()}:{loc.get_end_col()}"
        return f"{start}-{end}"


def ast_renderer(ctx: TreeRenderer.NodeContext) -> str:
    edge_label = TreeRenderer.format_edge_label(ctx.inbound_edge)
    type_description = TreeRenderer.describe_node(ctx, value_extractor=extract_value)
    return f"{edge_label}: {type_description}"


def typegraph_renderer(ctx: TreeRenderer.NodeContext) -> str:
    edge_label = TreeRenderer.format_edge_label(
        ctx.inbound_edge, prefix_on_anonymous=False
    )
    type_description = TreeRenderer.describe_node(ctx, value_extractor=extract_value)
    return f"{edge_label}: {type_description}"


def instancegraph_renderer(ctx: TreeRenderer.NodeContext, root: fabll.Node) -> str:
    edge_label = TreeRenderer.format_edge_label(ctx.inbound_edge)
    type_description = TreeRenderer.describe_node(ctx, value_extractor=extract_value)
    connections = TreeRenderer.collect_interface_connections(ctx.node, root)
    extras_text = " (" + ", ".join(connections) + ")" if connections else ""
    return f"{edge_label}: {type_description}{extras_text}"


def section(title: str, sep: str = "\n") -> None:
    print(sep + f" {title} ".center(80, "="))


app = typer.Typer(
    help="Debug ato compilation by visualizing AST, type graph, and instance graph.",
    rich_markup_mode="rich",
)


@app.command()
def main(
    file: Path = typer.Argument(..., exists=True, readable=True),
    entrypoint: str = typer.Argument(...),
) -> None:
    """Compile an ato file and visualize its compilation stages."""
    section("Build logs", sep="")
    graph = GraphView.create()

    stdlib_tg, stdlib_registry = build_stdlib(graph)
    result = build_file(graph, file.resolve())

    section("AST Graph")
    TreeRenderer.print_tree(result.ast_root.instance, renderer=ast_renderer)

    for type_name, type_root in result.state.type_roots.items():
        section(f"Pre-Link Type Graph: {type_name}")
        TreeRenderer.print_tree(type_root, renderer=typegraph_renderer)

    section("Linking", sep="\n\n")
    linker = Linker(config, stdlib_registry, stdlib_tg)
    linker.link_imports(graph, result.state)

    if entrypoint not in result.state.type_roots:
        available = ", ".join(result.state.type_roots.keys())
        typer.echo(
            f"Error: '{entrypoint}' not found in file. Available types: {available}",
            err=True,
        )
        raise typer.Exit(1)

    section(f"Post-Link Type Graph: {entrypoint}")
    app_type = result.state.type_roots[entrypoint]
    TreeRenderer.print_tree(app_type, renderer=typegraph_renderer)

    section("Instance Graph")
    app_type = result.state.type_roots[entrypoint]
    app_instance = result.state.type_graph.instantiate_node(
        type_node=app_type, attributes={}
    )
    TreeRenderer.print_tree(
        app_instance,
        renderer=lambda ctx: instancegraph_renderer(
            ctx, root=fabll.Node.bind_instance(app_instance)
        ),
    )


if __name__ == "__main__":
    app()
