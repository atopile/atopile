# This file is part of the atopile project
# SPDX-License-Identifier: MIT

"""Interactive visualizer for compiler graph nodes.

This mirrors the general approach used by
``faebryk.exporters.visualize.interactive_params`` but operates on the
``atopile.compiler.graph_types`` node hierarchy instead.  It builds a tree of the
compiler graph, colours nodes by coarse categories, and allows switching between
``fcose`` and ``dagre`` layouts for easier exploration of the structure parsed by
the compiler.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Sequence

import dash_cytoscape as cyto
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State

from atopile.compiler import graph_types as ct
from faebryk.core.node import Node
from faebryk.exporters.visualize.interactive_params_base import Layout
from faebryk.libs.util import typename


@dataclass(frozen=True)
class _Edge:
    parent: Node
    child: Node
    label: str


# Type grouping ------------------------------------------------------------------------

_GROUP_COLOURS = {
    "structure": "#E0F2F1",  # teal tint
    "statement": "#FFF3E0",  # soft orange
    "reference": "#E8F5E9",  # pale green
    "literal": "#F3E5F5",  # lilac
    "support": "#ECEFF1",  # grey-blue
}

_GROUP_TYPES: dict[str, tuple[type[Node], ...]] = {
    "structure": (
        ct.CompilationUnit,
        ct.File,
        ct.Scope,
        ct.BlockDefinition,
        ct.TextFragment,
    ),
    "statement": (
        ct.AssignNewStmt,
        ct.AssignQuantityStmt,
        ct.DeclarationStmt,
        ct.PragmaStmt,
        ct.ImportStmt,
        ct.ConnectStmt,
        ct.DirectedConnectStmt,
        ct.CumAssignStmt,
        ct.SetAssignStmt,
        ct.RetypeStmt,
        ct.SignaldefStmt,
        ct.AssertStmt,
        ct.PassStmt,
        ct.ForStmt,
        ct.PinDeclaration,
        ct.StringStmt,
    ),
    "reference": (
        ct.FieldRef,
        ct.FieldRefPart,
        ct.TypeRef,
        ct.Template,
        ct.TemplateArg,
    ),
    "literal": (
        ct.Quantity,
        ct.BilateralQuantity,
        ct.BoundedQuantity,
        ct.String,
        ct.Number,
        ct.Boolean,
    ),
    "support": (
        ct.SourceChunk,
        ct.Whitespace,
        ct.Comment,
    ),
}


def _group_for(node: Node) -> str:
    for group, types in _GROUP_TYPES.items():
        if isinstance(node, types):
            return group
    return "structure"


# Node labelling ----------------------------------------------------------------------


def _trim(text: str, limit: int = 60) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _extra_lines(node: Node) -> list[str]:
    match node:
        case ct.SourceChunk() as chunk:
            return (
                [f"text={_trim(chunk.text.replace('\n', '\\n'))}"] if chunk.text else []
            )
        case ct.PragmaStmt() as pragma:
            return [f"pragma={_trim(pragma.pragma)}"]
        case ct.ImportStmt() as imp:
            return [f"path={_trim(str(imp.path))}"] if imp.path else []
        case ct.AssignNewStmt() as stmt:
            extra: list[str] = []
            if stmt.new_count is not None:
                extra.append(f"count={stmt.new_count}")
            if stmt.template is not None:
                extra.append("template")
            return extra
        case ct.AssignQuantityStmt() as stmt:
            return ["quantity"] if stmt.quantity else []
        case ct.Quantity() as quantity:
            return [f"value={quantity.value}"]
        case ct.TypeRef() as tref:
            return [f"name={tref.name}"]
        case ct.FieldRefPart() as part:
            extra = [f"name={part.name}"]
            if part.key is not None:
                extra.append(f"key={part.key}")
            return extra
        case ct.String() as s:
            return [f"value={_trim(s.value)}"]
        case ct.Number() as n:
            return [f"value={n.value}"]
        case ct.Boolean() as b:
            return [f"value={b.value}"]
        case _:
            return []


def _node_label(node: Node) -> str:
    name = node.get_name(accept_no_parent=True) or "<anon>"
    type_name = typename(node)
    parts = [f"{name} ({type_name})"]
    parts.extend(_extra_lines(node))
    return "\n".join(parts)


# Graph extraction --------------------------------------------------------------------


def _node_children(node: Node) -> Iterable[Node]:
    return node.get_children(direct_only=True, types=Node, sort=False)


def _collect(root: Node) -> tuple[list[Node], list[_Edge]]:
    nodes: list[Node] = []
    edges: list[_Edge] = []
    seen: set[int] = set()

    def edge_label(child: Node, rel: str) -> str:
        name = child.get_name(accept_no_parent=True)
        if name and name != rel:
            label = name
        else:
            label = rel

        if label.startswith("runtime[") and label.endswith("]"):
            return label[len("runtime[") : -1]
        if label.startswith("runtime_anon[") and label.endswith("]"):
            inner = label[len("runtime_anon[") : -1]
            return inner if inner else "item"
        if ".[" in label:
            label = label.split(".")[-1]
        if label.endswith("]"):
            label = label.rsplit("[", 1)[0]
        return label

    def visit(node: Node) -> None:
        node_id = id(node)
        if node_id in seen:
            return
        seen.add(node_id)
        nodes.append(node)
        for child in _node_children(node):
            parent, rel = child.get_parent_force()
            label = edge_label(child, rel)
            edges.append(_Edge(parent=node, child=child, label=label))
            visit(child)

    visit(root)
    return nodes, edges


# Dash application --------------------------------------------------------------------


def _stylesheet() -> list[dict[str, Any]]:
    base = [
        {
            "selector": "node",
            "style": {
                "content": "data(label)",
                "text-valign": "center",
                "text-halign": "center",
                "font-size": "0.45em",
                "background-color": "#BFD7B5",
                "text-outline-color": "#FFFFFF",
                "text-outline-width": 0.5,
                "border-width": 1,
                "border-color": "#888888",
                "border-opacity": 0.6,
                "text-wrap": "wrap",
            },
        },
        {
            "selector": "edge",
            "style": {
                "width": 1,
                "line-color": "#A3C4BC",
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "arrow-scale": 0.8,
                "target-arrow-color": "#A3C4BC",
                "label": "data(label)",
                "font-size": "0.35em",
                "text-background-color": "#FFFFFF",
                "text-background-opacity": 0.7,
                "text-background-padding": 2,
            },
        },
    ]

    for group, colour in _GROUP_COLOURS.items():
        base.append(
            {
                "selector": f'node[group = "{group}"]',
                "style": {"background-color": colour},
            }
        )

    return base


def _build_elements(
    nodes: Sequence[Node], edges: Sequence[_Edge]
) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []

    for node in nodes:
        elements.append(
            {
                "data": {
                    "id": str(id(node)),
                    "label": _node_label(node),
                    "type": "node",
                    "group": _group_for(node),
                }
            }
        )

    for edge in edges:
        elements.append(
            {
                "data": {
                    "id": f"edge-{id(edge.parent)}-{id(edge.child)}",
                    "source": str(id(edge.parent)),
                    "target": str(id(edge.child)),
                    "label": edge.label,
                }
            }
        )

    return elements


def _add_controls(app: Dash, layout: Layout) -> None:
    layout_selector = dcc.RadioItems(
        id="compiler-layout-radio",
        options=[
            {"label": "fcose", "value": "fcose"},
            {"label": "dagre", "value": "dagre"},
        ],
        value="dagre",
        labelStyle={"display": "inline-block", "margin-right": "12px"},
    )

    rank_direction = dcc.RadioItems(
        id="compiler-rank-dir",
        options=[
            {"label": "Top → Bottom", "value": "TB"},
            {"label": "Left → Right", "value": "LR"},
        ],
        value="TB",
        labelStyle={"display": "inline-block", "margin-right": "12px"},
    )

    controls = html.Div(
        className="controls",
        style={
            "padding": "10px",
            "background-color": "#f5f5f5",
            "display": "flex",
            "gap": "20px",
            "align-items": "center",
        },
        children=[html.Div("Layout:"), layout_selector, rank_direction],
    )

    layout.div_children.insert(-2, controls)

    @app.callback(
        Output("graph-view", "layout"),
        Input("compiler-layout-radio", "value"),
        Input("compiler-rank-dir", "value"),
        State("graph-view", "layout"),
    )
    def update_layout(
        layout_choice: str, rank_dir: str, current_layout: dict[str, Any]
    ):
        layout.set_type(layout_choice, current_layout)
        if layout_choice == "dagre":
            current_layout["name"] = "dagre"
            current_layout["rankDir"] = rank_dir
        else:
            current_layout.pop("rankDir", None)
        return current_layout


def visualize_compiler_graph(root: Node, *, height: int | None = None) -> None:
    """Launch an interactive Dash visualizer for a compiler ``Node`` tree."""

    nodes, edges = _collect(root)
    elements = _build_elements(nodes, edges)

    stylesheet = _stylesheet()
    cyto.load_extra_layouts()

    app = Dash(__name__)
    app.layout = html.Div(
        style={
            "position": "fixed",
            "display": "flex",
            "flex-direction": "column",
            "height": "100%",
            "width": "100%",
        },
        children=[
            html.Div(
                className="cy-container",
                style={"flex": "1", "position": "relative"},
                children=[
                    cyto.Cytoscape(
                        id="graph-view",
                        stylesheet=stylesheet,
                        style={
                            "position": "absolute",
                            "width": "100%",
                            "height": "100%",
                            "zIndex": 999,
                        },
                        elements=elements,
                        layout={"name": "dagre", "rankDir": "TB"},
                    )
                ],
            ),
        ],
    )

    layout_state = Layout(app, elements, list(nodes))
    _add_controls(app, layout_state)

    app.run(jupyter_height=height or 1000)


__all__ = ["visualize_compiler_graph"]
