# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import dash_core_components as dcc
import dash_cytoscape as cyto
from dash import Dash, html
from dash.dependencies import Input, Output, State

# import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.link import LinkSibling
from faebryk.core.node import Node
from faebryk.core.parameter import Expression, Parameter
from faebryk.exporters.parameters.parameters_to_file import parameter_report
from faebryk.exporters.visualize.interactive_params_base import (
    _GROUP_TYPES,
    Layout,
    _Layout,
)
from faebryk.libs.util import (
    KeyErrorAmbiguous,
    find_or,
    typename,
)

Operand = Parameter | Expression


@dataclass(eq=True, frozen=True)
class ParamLink:
    operator: Expression
    operand: Operand


def _node(node: Operand):
    try:
        subtype = find_or(_GROUP_TYPES, lambda t: isinstance(node, t), default=Node)
    except KeyErrorAmbiguous as e:
        subtype = e.duplicates[0]

    hier = node.get_hierarchy()
    type_hier = [t for t, _ in hier]
    name_hier = [n for _, n in hier]
    name = ".".join(name_hier)
    types = "|".join(typename(t) for t in type_hier)
    label = f"{name}\n({types})"

    return {
        "data": {
            "id": str(id(node)),
            "label": label,
            "type": typename(subtype),
        }
    }


def _link(link: ParamLink):
    return {
        "data": {
            "source": str(id(link.operand)),
            "target": str(id(link.operator)),
        }
    }


class _Stylesheet:
    _BASE = [
        {
            "selector": "node",
            "style": {
                "content": "data(label)",
                "text-opacity": 0.8,
                "text-valign": "center",
                "text-halign": "center",
                "font-size": "0.3em",
                "background-color": "#BFD7B5",
                "text-outline-color": "#FFFFFF",
                "text-outline-width": 0.5,
                "border-width": 1,
                "border-color": "#888888",
                "border-opacity": 0.5,
                # group
                "font-weight": "bold",
                # "font-size": "1.5em",
                # "text-valign": "top",
                # "text-outline-color": "#FFFFFF",
                # "text-outline-width": 1.5,
                "text-wrap": "wrap",
                # "border-width": 4,
            },
        },
        {
            "selector": "edge",
            "style": {
                "width": 1,
                "line-color": "#A3C4BC",
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "arrow-scale": 1,
                "target-arrow-color": "#A3C4BC",
                "text-outline-color": "#FFFFFF",
                "text-outline-width": 2,
            },
        },
    ]

    def __init__(self):
        self.stylesheet = list(self._BASE)

    def add_node_type(self, node_type: str, color: str):
        self.stylesheet.append(
            {
                "selector": f'node[type = "{node_type}"]',
                "style": {"background-color": color},
            }
        )


DAGRE_LAYOUT = {
    # Dagre algorithm options (uses default value if undefined)
    "name": "dagre",
    # Separation between adjacent nodes in the same rank
    # "nodeSep": None,
    # Separation between adjacent edges in the same rank
    # "edgeSep": None,
    # Separation between each rank in the layout
    # "rankSep": None,
    # 'TB' for top to bottom flow, 'LR' for left to right
    # "rankDir": None,
    # Alignment for rank nodes. Can be 'UL', 'UR', 'DL', or 'DR'
    # "align": None,
    # If 'greedy', uses heuristic to find feedback arc set
    # "acyclicer": None,
    # Algorithm to assign rank to nodes: 'network-simplex', 'tight-tree'
    # or 'longest-path'
    # "ranker": "tight-tree",
    # Number of ranks to keep between source and target of the edge
    # "minLen": lambda edge: 1,
    # Higher weight edges are generally made shorter and straighter
    # "edgeWeight": lambda edge: 1,
    # General layout options
    # Whether to fit to viewport
    # "fit": True,
    # Fit padding
    # "padding": 30,
    # Factor to expand/compress overall area nodes take up
    # "spacingFactor": None,
    # Include labels in node space calculation
    # "nodeDimensionsIncludeLabels": False,
    # Whether to transition node positions
    # "animate": False,
    # Whether to animate specific nodes
    # "animateFilter": lambda node, i: True,
    # Duration of animation in ms if enabled
    # "animationDuration": 500,
    # Easing of animation if enabled
    # "animationEasing": None,
    # Constrain layout bounds: {x1, y1, x2, y2} or {x1, y1, w, h}
    # "boundingBox": None,
    # Function to transform final node position
    # "transform": lambda node, pos: pos,
    # Callback on layoutready
    # "ready": lambda: None,
    # Sorting function to order nodes and edges
    # "sort": None,
    # Callback on layoutstop
    # "stop": lambda: None,
}


def buttons(layout: Layout):
    app = layout.app

    layout_chooser = dcc.RadioItems(
        id="layout-radio",
        options=[
            {"label": "fcose", "value": "fcose"},
            {"label": "dagre", "value": "dagre"},
        ],
        value="dagre",
    )

    dagre_ranker = dcc.RadioItems(
        id="layout-dagre-ranker",
        options=[
            {"label": "network-simplex", "value": "network-simplex"},
            {"label": "tight-tree", "value": "tight-tree"},
            {"label": "longest-path", "value": "longest-path"},
        ],
        value="tight-tree",
    )

    html_controls = html.Div(
        className="controls",
        style={"padding": "10px", "background-color": "#f0f0f0"},
        children=[
            html.Table(
                [
                    html.Tr([html.Td("Layout:"), html.Td(layout_chooser)]),
                    html.Tr([html.Td("Dagre Ranker:"), html.Td(dagre_ranker)]),
                ]
            )
        ],
    )
    layout.div_children.insert(-2, html_controls)

    @app.callback(
        Output("graph-view", "layout"),
        Input("layout-radio", "value"),
        Input("layout-dagre-ranker", "value"),
        State("graph-view", "layout"),
    )
    def absolute_layout(layout_radio, layout_dagre_ranker, current_layout):
        # print(layout_radio, layout_dagre_ranker)
        layout.set_type(layout_radio, current_layout)

        if layout_dagre_ranker:
            current_layout["ranker"] = layout_dagre_ranker

        return current_layout


def visualize_parameters(G: Graph, height: int | None = None):
    Operand_ = (Parameter, Expression)
    nodes = GraphFunctions(G).nodes_of_types(Operand_)
    nodes = cast(list[Operand], nodes)

    edges = {
        ParamLink(n, e.node)
        for n in nodes
        if isinstance(n, Expression)
        for e, li in n.operates_on.edges.items()
        if not isinstance(li, LinkSibling)
        and e.node is not n
        and isinstance(e.node, Operand_)
    }

    # TODO filter equivalency classes

    parameter_report(G, Path("./build/params.txt"))

    elements = [_node(n) for n in nodes] + [_link(li) for li in edges]
    stylesheet = _Stylesheet()

    node_types_colors = [
        (typename(group_type), color) for group_type, color in _GROUP_TYPES.items()
    ]

    for node_type, color in node_types_colors:
        stylesheet.add_node_type(node_type, color)

    cyto.load_extra_layouts()
    app = Dash(__name__)
    app.layout = _Layout(stylesheet, elements, extra=DAGRE_LAYOUT)

    # Extra layouting
    layout = Layout(app, elements, list(nodes))
    buttons(layout)

    app.run(jupyter_height=height or 1400)
