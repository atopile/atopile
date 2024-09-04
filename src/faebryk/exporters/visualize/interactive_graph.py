# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import rich
import rich.text

from faebryk.core.graph import Graph
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.link import Link
from faebryk.core.node import Node
from faebryk.exporters.visualize.util import IDSet, generate_pastel_palette


def interactive_graph(G: Graph):
    import dash_cytoscape as cyto
    from dash import Dash, html

    # Register the fcose layout
    cyto.load_extra_layouts()

    app = Dash(__name__)

    node_types: set[str] = set()
    groups = {}

    def _group(gif: GraphInterface) -> str:
        node = gif.node
        my_node_id = str(id(node))
        if my_node_id not in groups:
            label = f"{node.get_full_name()} ({type(node).__name__})"
            groups[my_node_id] = {
                "data": {
                    "id": my_node_id,
                    "label": label,
                    "type": "group",
                }
            }

        return my_node_id

    def _node(node: Node):
        full_name = node.get_full_name()
        type_name = type(node).__name__
        node_types.add(type_name)
        data = {"id": str(id(node)), "label": full_name, "type": type_name}
        if isinstance(node, GraphInterface):
            data["parent"] = _group(node)
        return {"data": data}

    link_types: set[str] = set()
    links_touched = IDSet[Link]()

    def _link(link: Link):
        if link in links_touched:
            return None
        links_touched.add(link)

        try:
            source, target = tuple(str(id(n)) for n in link.get_connections())
        except ValueError:
            return None

        type_name = type(link).__name__
        link_types.add(type_name)

        return {"data": {"source": source, "target": target, "type": type_name}}

    def _not_none(x):
        return x is not None

    elements = [
        *(filter(_not_none, (_node(gif) for gif in G))),
        *(
            filter(
                _not_none,
                (_link(link) for gif in G for link in gif.get_links()),
            )
        ),
        *(
            groups.values()
        ),  # must go after nodes because the node iteration creates the groups
    ]

    stylesheet = [
        {
            "selector": "node",
            "style": {
                "content": "data(label)",
                "text-opacity": 0.8,
                "text-valign": "center",
                "text-halign": "center",
                "background-color": "#BFD7B5",
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
            },
        },
    ]

    def _pastels(iterable):
        return zip(iterable, generate_pastel_palette(len(iterable)))

    for node_type, color in _pastels(node_types):
        stylesheet.append(
            {
                "selector": f'node[type = "{node_type}"]',
                "style": {"background-color": color},
            }
        )

    stylesheet.append(
        {
            "selector": 'node[type = "group"]',
            "style": {
                "background-color": "#D3D3D3",
                "font-weight": "bold",
                "font-size": "1.5em",
                "text-valign": "top",
            },
        }
    )

    for link_type, color in _pastels(link_types):
        stylesheet.append(
            {
                "selector": f'edge[type = "{link_type}"]',
                "style": {"line-color": color, "target-arrow-color": color},
            }
        )

    container_style = {
        "position": "fixed",
        "display": "flex",
        "flex-direction": "column",
        "height": "100%",
        "width": "100%",
    }

    graph_view_style = {
        "position": "absolute",
        "width": "100%",
        "height": "100%",
        "zIndex": 999,
    }

    _cyto = cyto.Cytoscape(
        id="graph-view",
        stylesheet=stylesheet,
        style=graph_view_style,
        elements=elements,
        layout={
            "name": "fcose",
            "quality": "proof",
            "animate": False,
            "randomize": False,
            "fit": True,
            "padding": 50,
            "nodeDimensionsIncludeLabels": True,
            "uniformNodeDimensions": False,
            "packComponents": True,
            "nodeRepulsion": 8000,
            "idealEdgeLength": 50,
            "edgeElasticity": 0.45,
            "nestingFactor": 0.1,
            "gravity": 0.25,
            "numIter": 2500,
            "tile": True,
            "tilingPaddingVertical": 10,
            "tilingPaddingHorizontal": 10,
            "gravityRangeCompound": 1.5,
            "gravityCompound": 1.0,
            "gravityRange": 3.8,
            "initialEnergyOnIncremental": 0.5,
        },
    )

    app.layout = html.Div(
        style=container_style,
        children=[
            html.Div(
                className="cy-container",
                style={"flex": "1", "position": "relative"},
                children=[_cyto],
            ),
        ],
    )

    # print the color palette
    print("Node types:")
    for node_type, color in _pastels(node_types):
        colored_text = rich.text.Text(f"{node_type}: {color}")
        colored_text.stylize(f"on {color}")
        rich.print(colored_text)
    print("\n")

    print("Link types:")
    for link_type, color in _pastels(link_types):
        colored_text = rich.text.Text(f"{link_type}: {color}")
        colored_text.stylize(f"on {color}")
        rich.print(colored_text)
    print("\n")

    app.run()
