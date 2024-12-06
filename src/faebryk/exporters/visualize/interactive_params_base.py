# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

# TODO this used to be interactive_graph.py
# merge it back into it

from itertools import pairwise
from typing import Any, Callable, Collection, Iterable

import dash_core_components as dcc
import dash_cytoscape as cyto
from dash import Dash, html
from dash.dependencies import Input, Output, State
from rich.console import Console
from rich.table import Table

# import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.link import Link, LinkSibling
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.core.parameter import Expression, Parameter, Predicate
from faebryk.core.trait import Trait
from faebryk.exporters.visualize.util import generate_pastel_palette
from faebryk.libs.util import KeyErrorAmbiguous, cast_assert, find_or, groupby, typename


# Transformers -------------------------------------------------------------------------
def _gif(gif: GraphInterface):
    return {
        "data": {
            "id": str(id(gif)),
            "label": gif.name,
            "type": typename(gif),
            "parent": str(id(gif.node)),
        }
    }


def _link(source, target, link: Link):
    return {
        "data": {
            "source": str(id(source)),
            "target": str(id(target)),
            "type": typename(link),
        }
    }


_GROUP_TYPES = {
    Predicate: "#FCF3CF",  # Very light goldenrod
    Expression: "#D1F2EB",  # Very soft turquoise
    Parameter: "#FFD9DE",  # Very light pink
    Module: "#E0F0FF",  # Very light blue
    Trait: "#FCFCFF",  # Almost white
    # F.Electrical: "#D1F2EB",  # Very soft turquoise
    # F.ElectricPower: "#FCF3CF",  # Very light goldenrod
    # F.ElectricLogic: "#EBE1F1",  # Very soft lavender
    # Defaults
    ModuleInterface: "#DFFFE4",  # Very light green
    Node: "#FCFCFF",  # Almost white
}


def _group(node: Node, root: bool):
    try:
        subtype = find_or(_GROUP_TYPES, lambda t: isinstance(node, t), default=Node)
    except KeyErrorAmbiguous as e:
        subtype = e.duplicates[0]

    if root:
        hier = node.get_hierarchy()
        type_hier = [t for t, _ in hier]
        name_hier = [n for _, n in hier]
        name = ".".join(name_hier)
        types = "|".join(typename(t) for t in type_hier)
        label = f"{name}\n({types})"
    else:
        label = f"{node.get_name(accept_no_parent=True)}\n({typename(node)})"

    return {
        "data": {
            "id": str(id(node)),
            "label": label,
            "type": "group",
            "subtype": typename(subtype),
            "parent": str(id(p[0])) if (p := node.get_parent()) else None,
        }
    }


# Style --------------------------------------------------------------------------------


def _with_pastels(iterable: Collection[str]):
    return zip(sorted(iterable), generate_pastel_palette(len(iterable)))


class _Stylesheet:
    _BASE = [
        {
            "selector": "node",
            "style": {
                "content": "data(label)",
                "text-opacity": 0.8,
                "text-valign": "center",
                "text-halign": "center",
                "font-size": "0.5em",
                "background-color": "#BFD7B5",
                "text-outline-color": "#FFFFFF",
                "text-outline-width": 0.5,
                "border-width": 1,
                "border-color": "#888888",
                "border-opacity": 0.5,
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
        {
            "selector": 'node[type = "group"]',
            "style": {
                "background-color": "#D3D3D3",
                "font-weight": "bold",
                "font-size": "1.5em",
                "text-valign": "top",
                "text-outline-color": "#FFFFFF",
                "text-outline-width": 1.5,
                "text-wrap": "wrap",
                "border-width": 4,
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

    def add_link_type(self, link_type: str, color: str):
        self.stylesheet.append(
            {
                "selector": f'edge[type = "{link_type}"]',
                "style": {
                    "line-color": color,
                    "target-arrow-color": color,
                    # "target-arrow-shape": "none",
                    # "source-arrow-shape": "none",
                },
            }
        )

    def add_group_type(self, group_type: str, color: str):
        self.stylesheet.append(
            {
                "selector": f'node[subtype = "{group_type}"]',
                "style": {"background-color": color},
            }
        )


def _Layout(
    stylesheet: _Stylesheet, elements: list[dict[str, dict]], extra: dict | None = None
):
    if not extra:
        extra = {}
    return html.Div(
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
                        stylesheet=stylesheet.stylesheet,
                        style={
                            "position": "absolute",
                            "width": "100%",
                            "height": "100%",
                            "zIndex": 999,
                        },
                        elements=elements,
                        layout={
                            "name": "fcose",
                        }
                        | extra,
                    )
                ],
            ),
        ],
    )


def _get_layout(app: Dash) -> dict[str, Any]:
    for html_node in cast_assert(list, cast_assert(html.Div, app.layout).children):
        if not isinstance(html_node, html.Div):
            continue
        for child in cast_assert(list, html_node.children):
            if not isinstance(child, cyto.Cytoscape):
                continue
            return child.layout
    raise ValueError("No Cytoscape found in layout")


# --------------------------------------------------------------------------------------


class Layout:
    type ID_or_OBJECT = object | str

    def __init__(self, app: Dash, elements: list[dict], nodes: list[Node]):
        self.app = app
        self.layout = _get_layout(app)
        self.ids = {
            element["data"]["id"] for element in elements if "id" in element["data"]
        }

        self.div_children = cast_assert(
            list, cast_assert(html.Div, app.layout).children
        )
        self.nodes = nodes

    def is_filtered(self, elem: ID_or_OBJECT) -> bool:
        if not isinstance(elem, str):
            elem = self.id_of(elem)
        return elem not in self.ids

    def nodes_of_type[T: Node](self, node_type: type[T]) -> set[T]:
        return {
            n
            for n in self.nodes
            if isinstance(n, node_type) and not self.is_filtered(n.self_gif)
        }

    @staticmethod
    def id_of(obj: ID_or_OBJECT) -> str:
        if isinstance(obj, str):
            return obj
        return str(id(obj))

    def add_rel_constraint(
        self,
        source: ID_or_OBJECT,
        target: ID_or_OBJECT,
        gap_x: int | None = None,
        gap_y: int | None = None,
        layout: dict | None = None,
    ):
        if not layout:
            layout = self.layout

        if "relativePlacementConstraint" not in layout:
            layout["relativePlacementConstraint"] = []
        rel_placement_constraints = cast_assert(
            list, layout["relativePlacementConstraint"]
        )

        if self.is_filtered(source) or self.is_filtered(target):
            return
        if gap_y is not None:
            top, bot = (source, target) if gap_y >= 0 else (target, source)

            # if isinstance(top, GraphInterface) and isinstance(bot, GraphInterface):
            #     print(f"{top}\n   v\n{bot}")

            rel_placement_constraints.append(
                {
                    "top": self.id_of(top),
                    "bottom": self.id_of(bot),
                    "gap": abs(gap_y),
                }
            )
        if gap_x is not None:
            left, right = (source, target) if gap_x >= 0 else (target, source)

            # if isinstance(left, GraphInterface) and isinstance(right, GraphInterface):
            #    print(f"{left} > {right}")

            rel_placement_constraints.append(
                {
                    "left": self.id_of(left),
                    "right": self.id_of(right),
                    "gap": abs(gap_x),
                }
            )

    def add_rel_top_bot(
        self,
        top: ID_or_OBJECT,
        bot: ID_or_OBJECT,
        gap: int = 0,
        layout: dict | None = None,
    ):
        assert gap >= 0
        self.add_rel_constraint(top, bot, gap_y=gap, layout=layout)

    def add_rel_left_right(
        self,
        left: ID_or_OBJECT,
        right: ID_or_OBJECT,
        gap: int = 0,
        layout: dict | None = None,
    ):
        assert gap >= 0
        self.add_rel_constraint(left, right, gap_x=gap, layout=layout)

    def add_order(
        self,
        *nodes: ID_or_OBJECT,
        horizontal: bool,
        gap: int = 0,
        layout: dict | None = None,
    ):
        if not layout:
            layout = self.layout
        for n1, n2 in pairwise(nodes):
            if horizontal:
                self.add_rel_left_right(n1, n2, gap=gap, layout=layout)
            else:
                self.add_rel_top_bot(n1, n2, gap=gap, layout=layout)

    def add_align(
        self, *nodes: ID_or_OBJECT, horizontal: bool, layout: dict | None = None
    ):
        if not layout:
            layout = self.layout
        direction = "horizontal" if horizontal else "vertical"
        nodes = tuple(n for n in nodes if not self.is_filtered(n))
        if len(nodes) <= 1:
            return

        # if all(isinstance(n, GraphInterface) for n in nodes):
        #     print(f"align {direction}: {nodes}")

        if "alignmentConstraint" not in layout:
            layout["alignmentConstraint"] = {}
        if direction not in layout["alignmentConstraint"]:
            layout["alignmentConstraint"][direction] = []

        align = cast_assert(dict, layout["alignmentConstraint"])
        align[direction].append([self.id_of(n) for n in nodes])

    def add_same_height[T: Node](
        self,
        nodes: Iterable[T],
        gif_key: Callable[[T], GraphInterface],
        layout: dict | None = None,
    ):
        if not layout:
            layout = self.layout
        self.add_align(*(gif_key(n) for n in nodes), horizontal=True, layout=layout)

    def set_type(self, t: str, layout: dict | None = None):
        if not layout:
            layout = self.layout
        if t == "fcose" or t is None:
            _layout = {
                "name": "fcose",
                # 'draft', 'default' or 'proof'
                # - "draft" only applies spectral layout
                # - "default" improves the quality with incremental layout
                #   (fast cooling rate)
                # - "proof" improves the quality with incremental layout
                #   (slow cooling rate)
                "quality": "proof",
                # Whether or not to animate the layout
                "animate": False,
                # Use random node positions at beginning of layout
                # if this is set to false,
                # then quality option must be "proof"
                "randomize": False,
                # Fit the viewport to the repositioned nodes
                "fit": True,
                # Padding around layout
                "padding": 50,
                # Whether to include labels in node dimensions.
                # Valid in "proof" quality
                "nodeDimensionsIncludeLabels": True,
                # Whether or not simple nodes (non-compound nodes)
                #  are of uniform dimensions
                "uniformNodeDimensions": True,
                # Whether to pack disconnected components -
                # cytoscape-layout-utilities extension should
                # be registered and initialized
                "packComponents": False,  # Graph is never disconnected
                # Node repulsion (non overlapping) multiplier
                "nodeRepulsion": 100,
                # Ideal edge (non nested) length
                "idealEdgeLength": 100,
                # Divisor to compute edge forces
                "edgeElasticity": 0.2,
                # Nesting factor (multiplier) to compute ideal edge length
                # for nested edges
                "nestingFactor": 0.0001,
                # Maximum number of iterations to perform -
                # this is a suggested value and might be adjusted by the
                #  algorithm as required
                "numIter": 2500 * 4,
                # For enabling tiling
                "tile": False,  # No unconnected nodes in Graph
                # Gravity force (constant)
                "gravity": 0,
                # Gravity range (constant)
                "gravityRange": 3.8,
                # Gravity force (constant) for compounds
                "gravityCompound": 20,
                # Gravity range (constant) for compounds
                "gravityRangeCompound": 0.5,
                # Initial cooling factor for incremental layout
                "initialEnergyOnIncremental": 0.5,
                "componentSpacing": 40,
            }
        elif t == "dagre":
            _layout = {
                "name": "dagre",
            }
        else:
            raise ValueError(f"Unknown layout: {t}")

        layout.clear()
        layout.update(_layout)


def buttons(layout: Layout):
    app = layout.app
    html_controls = html.Div(
        className="controls",
        style={"padding": "10px", "background-color": "#f0f0f0"},
        children=[
            #         html.Label("Node Repulsion:"),
            #         dcc.Slider(
            #             id="node-repulsion-slider",
            #             min=500,
            #             max=5000,
            #             step=100,
            #             value=1000,
            #             marks={i: str(i) for i in range(500, 5001, 500)},
            #         ),
            #         html.Label("Edge Elasticity:"),
            #         dcc.Slider(
            #             id="edge-elasticity-slider",
            #             min=0,
            #             max=1,
            #             step=0.05,
            #             value=0.45,
            #             marks={i / 10: str(i / 10) for i in range(0, 11, 1)},
            #         ),
            dcc.RadioItems(
                id="layout-radio",
                options=[
                    {"label": "fcose", "value": "fcose"},
                    {"label": "dagre", "value": "dagre"},
                ],
            ),
            dcc.RadioItems(
                id="layout-dagre-ranker",
                options=[
                    {"label": "network-simplex", "value": "network-simplex"},
                    {"label": "tight-tree", "value": "tight-tree"},
                    {"label": "longest-path", "value": "longest-path"},
                ],
            ),
            dcc.Checklist(
                id="layout-checkbox",
                options=[{"label": "Parameters", "value": "parameters"}],
            ),
            html.Button("Apply Changes", id="apply-changes-button"),
        ],
    )
    layout.div_children.insert(-2, html_controls)

    @app.callback(
        Output("graph-view", "layout"),
        Input("apply-changes-button", "n_clicks"),
        State("layout-checkbox", "value"),
        State("layout-radio", "value"),
        State("layout-dagre-ranker", "value"),
        State("graph-view", "layout"),
    )
    def absolute_layout(
        n_clicks, layout_checkbox, layout_radio, layout_dagre_ranker, current_layout
    ):
        print(layout_checkbox, layout_radio, layout_dagre_ranker)
        layout.set_type(layout_radio, current_layout)

        if layout_radio == "fcose":
            layout_constraints(layout, current_layout)

        if "parameters" in (layout_checkbox or []):
            params_top(layout, current_layout)

        if layout_dagre_ranker:
            current_layout["ranker"] = layout_dagre_ranker

        return current_layout


def params_top(layout: Layout, _layout: dict | None = None):
    params = layout.nodes_of_type(Parameter)
    expressions = layout.nodes_of_type(Expression)
    predicates = layout.nodes_of_type(Predicate)
    non_predicate_expressions = expressions - predicates

    def depth(expr: Expression) -> int:
        operates_on = expressions & {
            e.node
            for e, li in expr.operates_on.edges.items()
            if not isinstance(li, LinkSibling) and e.node is not expr
        }

        # direct parameter or constants only
        if not operates_on:
            return 1
        return 1 + max(depth(o) for o in operates_on)

    expressions_by_depth = groupby(non_predicate_expressions, depth)

    def same_height[T: Parameter | Expression](nodes: Iterable[T]):
        layout.add_same_height(nodes, lambda pe: pe.self_gif, layout=_layout)
        layout.add_same_height(nodes, lambda pe: pe.operated_on, layout=_layout)

    # All params same height
    same_height(params)

    # predicates same height
    same_height(predicates)

    for _, exprs in expressions_by_depth.items():
        same_height(exprs)

    # predicate expressions below other expressions
    if predicates:
        for expr in non_predicate_expressions:
            layout.add_rel_top_bot(
                expr.operates_on, next(iter(predicates)).self_gif, gap=200
            )

    # Expressions below params
    if params:
        for expr in expressions:
            layout.add_rel_top_bot(
                next(iter(params)).operated_on, expr.self_gif, gap=200
            )

    # Expression tree
    for expr in expressions:
        operates_on = (params | expressions) & {
            e.node
            for e, li in expr.operates_on.edges.items()
            if not isinstance(li, LinkSibling) and e.node is not expr
        }
        for o in operates_on:
            layout.add_rel_top_bot(o.operated_on, expr.self_gif, gap=100)


def layout_constraints(layout: Layout, _layout: dict | None = None):
    for n in layout.nodes:
        # only to save on some printing
        if layout.is_filtered(n.self_gif):
            continue

        siblings = {
            o
            for o, li in n.self_gif.edges.items()
            if isinstance(li, LinkSibling) and not layout.is_filtered(o)
        }

        # siblings below self
        for o in siblings:
            layout.add_rel_top_bot(n.self_gif, o, gap=50, layout=_layout)

        # siblings on same level within node
        layout.add_align(*siblings, horizontal=True, layout=_layout)

        order = list(sorted(siblings, key=lambda o: o.name))
        middle_i = len(order) // 2
        if len(siblings) % 2 == 1:
            # sibling directly below self
            layout.add_align(
                n.self_gif, order[middle_i], horizontal=False, layout=_layout
            )
            order.pop(middle_i)

        # self inbetween siblings
        order.insert(middle_i, n.self_gif)
        layout.add_order(*order, horizontal=True, gap=25, layout=_layout)


# --------------------------------------------------------------------------------------


def interactive_subgraph(
    edges: Iterable[tuple[GraphInterface, GraphInterface, Link]],
    gifs: list[GraphInterface],
    nodes: Iterable[Node],
    height: int | None = None,
):
    links = [link for _, _, link in edges]
    link_types = {typename(link) for link in links}
    gif_types = {typename(gif) for gif in gifs}

    def node_has_parent_in_graph(node: Node) -> bool:
        p = node.get_parent()
        if not p:
            return False
        return p[0] in nodes

    elements = (
        [_gif(gif) for gif in gifs]
        + [_link(*edge) for edge in edges]
        + [_group(node, root=not node_has_parent_in_graph(node)) for node in nodes]
    )

    # Build stylesheet
    stylesheet = _Stylesheet()

    gif_type_colors = list(_with_pastels(gif_types))
    link_type_colors = list(_with_pastels(link_types))
    group_types_colors = [
        (typename(group_type), color) for group_type, color in _GROUP_TYPES.items()
    ]

    for gif_type, color in gif_type_colors:
        stylesheet.add_node_type(gif_type, color)

    for link_type, color in link_type_colors:
        stylesheet.add_link_type(link_type, color)

    for group_type, color in group_types_colors:
        stylesheet.add_group_type(group_type, color)

    # Register the fcose layout
    cyto.load_extra_layouts()
    app = Dash(__name__)
    app.layout = _Layout(stylesheet, elements)

    # Extra layouting
    layout = Layout(app, elements, list(nodes))
    buttons(layout)

    # Print legend ---------------------------------------------------------------------
    console = Console()

    for typegroup, colors in [
        ("GIF", gif_type_colors),
        ("Link", link_type_colors),
        ("Node", group_types_colors),
    ]:
        table = Table(title="Legend")
        table.add_column("Type", style="cyan")
        table.add_column("Color", style="green")
        table.add_column("Name")

        for text, color in colors:
            table.add_row(typegroup, f"[on {color}]    [/]", text)

        console.print(table)

    # Run ------------------------------------------------------------------------------

    app.run(jupyter_height=height or 1000)


def interactive_graph(
    G: Graph,
    node_types: tuple[type[Node], ...] | None = None,
    depth: int = 0,
    filter_unconnected: bool = True,
    height: int | None = None,
):
    if node_types is None:
        node_types = (Node,)

    # Build elements
    nodes = GraphFunctions(G).nodes_of_types(node_types)
    if depth > 0:
        nodes = [node for node in nodes if len(node.get_hierarchy()) <= depth]

    gifs = {gif for gif in G.get_gifs() if gif.node in nodes}
    if filter_unconnected:
        gifs = [gif for gif in gifs if len(gif.edges.keys() & gifs) > 1]

    edges = [
        (edge[0], edge[1], edge[2])
        for edge in G.edges
        if edge[0] in gifs and edge[1] in gifs
    ]
    return interactive_subgraph(edges, list(gifs), nodes, height=height)
