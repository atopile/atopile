"""Interactive inspector for Faebryk PCB graphs.

This utility focuses on exploring the graph emitted by
``atopile.pcb_transformer.load_pcb_graph``. Users can pick a start node and
adjust the number of graph hops that should be rendered. The view updates in
real time and highlights the chosen entry node so it is easy to keep track of
the current focus.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

import dash_cytoscape as cyto
from dash import Dash, ctx, dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from faebryk.core.graph import Graph
from faebryk.core.node import Node
from faebryk.core.pcbgraph import (
    ArcNode,
    KicadLayerNode,
    PCBNode,
    XYRNode,
    ZoneNode,
)
from faebryk.exporters.visualize.interactive_graph import (
    _GROUP_TYPES,
    _gif,
    _group,
    _link,
    _Stylesheet,
    _with_pastels,
)
from faebryk.libs.util import typename


@dataclass(slots=True)
class _GraphCaches:
    """Pre-computed views that the Dash callbacks close over."""

    graph: Graph
    gif_lookup: Mapping[str, Any]
    node_lookup: Mapping[str, Node]
    node_to_self_gif: Mapping[str, str]
    node_id_to_name: Mapping[str, str]
    gif_id_to_node_name: Mapping[str, str]
    edges: Sequence[tuple[str, str, Any]]
    adjacency: Mapping[str, tuple[str, ...]]
    stylesheet: _Stylesheet
    default_entry: str
    current_entry: str
    history: list[str]
    ignore_entry_change: bool = False


def _build_adjacency(
    gif_lookup: Mapping[str, Any],
    graph_edges: Sequence[tuple[str, str, Any]],
) -> dict[str, tuple[str, ...]]:
    adjacency: MutableMapping[str, set[str]] = {gid: set() for gid in gif_lookup}
    for src_id, dst_id, _ in graph_edges:
        adjacency.setdefault(src_id, set()).add(dst_id)
        adjacency.setdefault(dst_id, set()).add(src_id)
    return {node: tuple(neigh) for node, neigh in adjacency.items()}


def _compute_distances(
    start: str, adjacency: Mapping[str, Iterable[str]]
) -> dict[str, int]:
    visited = {start: 0}
    queue: deque[str] = deque([start])
    while queue:
        current = queue.popleft()
        depth = visited[current] + 1
        for neighbor in adjacency.get(current, ()):  # pragma: no branch - defensive
            if neighbor in visited:
                continue
            visited[neighbor] = depth
            queue.append(neighbor)
    return visited


def _build_slider_marks(max_depth: int) -> dict[int, str]:
    if max_depth <= 10:
        steps = range(0, max_depth + 1)
    else:
        stride = max(1, max_depth // 10)
        steps = list(range(0, max_depth + 1, stride))
        if steps[-1] != max_depth:
            steps.append(max_depth)
    return {int(step): str(step) for step in steps}


def _build_stylesheet(graph: Graph, gif_lookup: Mapping[str, Any]) -> _Stylesheet:
    stylesheet = _Stylesheet()
    gif_type_colors = list(
        _with_pastels({typename(gif) for gif in gif_lookup.values()})
    )
    link_type_colors = list(_with_pastels({typename(link) for *_, link in graph.edges}))
    group_types_colors = [
        (typename(group_type), color) for group_type, color in _GROUP_TYPES.items()
    ]

    for gif_type, color in gif_type_colors:
        stylesheet.add_node_type(gif_type, color)

    for link_type, color in link_type_colors:
        stylesheet.add_link_type(link_type, color)

    for group_type, color in group_types_colors:
        stylesheet.add_group_type(group_type, color)

    stylesheet.stylesheet.extend(
        [
            {
                "selector": ".root-node",
                "style": {
                    "background-color": "#FFE0B2",
                    "border-color": "#FF9800",
                    "border-width": 4,
                },
            },
            {
                "selector": "[is_root_node = 'true']",
                "style": {
                    "background-color": "#FFE0B2",
                    "border-color": "#FF9800",
                    "border-width": 4,
                },
            },
            {
                "selector": ".root-gif",
                "style": {
                    "background-color": "#FFECB3",
                    "border-color": "#FB8C00",
                    "border-width": 3,
                },
            },
            {
                "selector": "[is_root_gif = 'true']",
                "style": {
                    "background-color": "#FFECB3",
                    "border-color": "#FB8C00",
                    "border-width": 3,
                },
            },
            {
                "selector": ".root-edge",
                "style": {
                    "line-color": "#FB8C00",
                    "target-arrow-color": "#FB8C00",
                    "width": 2,
                },
            },
            {
                "selector": "[is_root_edge = 'true']",
                "style": {
                    "line-color": "#FB8C00",
                    "target-arrow-color": "#FB8C00",
                    "width": 2,
                },
            },
        ]
    )
    return stylesheet


def _build_elements(
    caches: _GraphCaches,
    included_ids: set[str],
    entry_name: str,
) -> list[dict[str, Any]]:
    gif_lookup = caches.gif_lookup
    node_lookup = caches.node_lookup
    highlight = node_lookup[entry_name]

    gifs = [gif_lookup[gid] for gid in included_ids if gid in gif_lookup]
    edges = [
        (gif_lookup[src], gif_lookup[dst], link)
        for src, dst, link in caches.edges
        if src in included_ids and dst in included_ids
    ]
    nodes = {gif.node for gif in gifs}

    elements: list[dict[str, Any]] = []

    def _assign_class(element: dict[str, Any], *, cls: str, enabled: bool) -> None:
        existing = element.get("classes", "")
        parts = {part for part in existing.split() if part}
        if enabled:
            parts.add(cls)
        else:
            parts.discard(cls)
        if parts:
            element["classes"] = " ".join(sorted(parts))
        else:
            element.pop("classes", None)

    for gif in gifs:
        element = _gif(gif)
        data = element.setdefault("data", {})
        data["node_full_name"] = gif.node.get_full_name()
        is_root = gif.node is highlight
        data["is_root_gif"] = "true" if is_root else "false"
        _assign_class(element, cls="root-gif", enabled=is_root)
        elements.append(element)

    for src, dst, link in edges:
        element = _link(src, dst, link)
        data = element.setdefault("data", {})
        is_root_edge = src.node is highlight or dst.node is highlight
        data["is_root_edge"] = "true" if is_root_edge else "false"
        _assign_class(element, cls="root-edge", enabled=is_root_edge)
        elements.append(element)

    for node in nodes:
        element = _group(node)
        data = element.setdefault("data", {})
        data["node_full_name"] = node.get_full_name()
        is_root_node = node is highlight
        data["is_root_node"] = "true" if is_root_node else "false"
        _assign_class(element, cls="root-node", enabled=is_root_node)
        elements.append(element)

    return elements


def _selection_summary(
    caches: _GraphCaches,
    included_ids: set[str],
    depth: int,
) -> str:
    nodes = {
        caches.gif_lookup[gid].node for gid in included_ids if gid in caches.gif_lookup
    }
    edge_count = sum(
        1
        for src_id, dst_id, _ in caches.edges
        if src_id in included_ids and dst_id in included_ids
    )
    return (
        f"Showing ≤{depth} hops · {len(included_ids)} interfaces · "
        f"{len(nodes)} nodes · {edge_count} edges"
    )


def _resolve_entry_name(entry: str, node_lookup: Mapping[str, Node]) -> str:
    if entry in node_lookup:
        return entry

    lowered = entry.lower()
    suffix_matches = [name for name in node_lookup if name.lower().endswith(lowered)]
    if len(suffix_matches) == 1:
        return suffix_matches[0]

    substring_matches = [name for name in node_lookup if lowered in name.lower()]
    if len(substring_matches) == 1:
        return substring_matches[0]

    options = suffix_matches or substring_matches
    suggestion = (
        f". Did you mean one of: {', '.join(sorted(options))}?" if options else ""
    )
    raise ValueError(f"Could not resolve entry node '{entry}'{suggestion}")


def _prepare_caches(
    graph_or_node: Graph | Node,
    entry: Node | str | None,
) -> _GraphCaches:
    graph = (
        graph_or_node if isinstance(graph_or_node, Graph) else graph_or_node.get_graph()
    )
    node_candidates = sorted(graph.node_projection(), key=lambda n: n.get_full_name())
    if not node_candidates:
        raise ValueError("Graph has no nodes to visualize")

    gif_lookup = {str(id(gif)): gif for gif in graph.get_gifs()}
    node_lookup = {node.get_full_name(): node for node in node_candidates}
    node_to_self_gif: dict[str, str] = {}
    node_id_to_name: dict[str, str] = {}
    gif_id_to_node_name: dict[str, str] = {}
    for name, node in node_lookup.items():
        matching_gif = next(
            (gid for gid, gif in gif_lookup.items() if gif.node is node),
            None,
        )
        node_to_self_gif[name] = matching_gif or str(id(node.self_gif))
        node_id_to_name[str(id(node))] = name
    for gif_id, gif in gif_lookup.items():
        node_name = gif.node.get_full_name()
        gif_id_to_node_name[gif_id] = node_name
    graph_edges = [(str(id(src)), str(id(dst)), link) for src, dst, link in graph.edges]
    adjacency = _build_adjacency(gif_lookup, graph_edges)
    stylesheet = _build_stylesheet(graph, gif_lookup)

    if isinstance(entry, Node):
        entry_name = entry.get_full_name()
    elif isinstance(entry, str):
        entry_name = _resolve_entry_name(entry, node_lookup)
    elif isinstance(graph_or_node, Node):
        entry_name = graph_or_node.get_full_name()
    else:
        entry_name = node_candidates[0].get_full_name()

    if entry_name not in node_to_self_gif:
        raise ValueError(f"Entry node '{entry_name}' is not part of the graph")

    return _GraphCaches(
        graph=graph,
        gif_lookup=gif_lookup,
        node_lookup=node_lookup,
        node_to_self_gif=node_to_self_gif,
        node_id_to_name=node_id_to_name,
        gif_id_to_node_name=gif_id_to_node_name,
        edges=graph_edges,
        adjacency=adjacency,
        stylesheet=stylesheet,
        default_entry=entry_name,
        current_entry=entry_name,
        history=[],
    )


def launch_pcb_graph_viewer(
    graph_or_node: Graph | Node,
    entry: Node | str | None = None,
    *,
    title: str | None = None,
    height: int | None = None,
) -> None:
    """Launch the Dash application for exploring a PCB graph."""

    caches = _prepare_caches(graph_or_node, entry)

    default_entry = caches.default_entry
    start_id = caches.node_to_self_gif[default_entry]
    default_distances = _compute_distances(start_id, caches.adjacency)
    default_max_depth = max(default_distances.values(), default=0)
    default_slider_value = 0 if default_max_depth == 0 else 1
    default_slider_value = min(default_slider_value, default_max_depth)
    default_marks = _build_slider_marks(default_max_depth)

    included_ids = {
        gif_id
        for gif_id, distance in default_distances.items()
        if distance <= default_slider_value
    }
    if not included_ids:
        included_ids.add(start_id)

    initial_elements = _build_elements(caches, included_ids, default_entry)
    initial_summary = _selection_summary(caches, included_ids, default_slider_value)

    cyto.load_extra_layouts()
    app = Dash(__name__)
    app.title = title or "PCB Graph Viewer"

    controls = html.Div(
        style={
            "padding": "0.75rem 1rem",
            "backgroundColor": "#f7f7f7",
            "borderBottom": "1px solid #dddddd",
            "display": "flex",
            "flexWrap": "wrap",
            "gap": "1rem",
            "alignItems": "center",
        },
        children=[
            html.Button(
                "Back",
                id="back-button",
                n_clicks=0,
                disabled=True,
                style={
                    "padding": "0.35rem 0.75rem",
                    "borderRadius": "4px",
                    "border": "1px solid #ccc",
                    "backgroundColor": "#fafafa",
                    "cursor": "pointer",
                },
            ),
            html.Div(
                style={"minWidth": "260px"},
                children=[
                    html.Label("Entry node", htmlFor="entry-node"),
                    dcc.Dropdown(
                        id="entry-node",
                        options=[
                            {"label": name, "value": name}
                            for name in caches.node_lookup
                        ],
                        value=caches.default_entry,
                        placeholder="Select a node…",
                        clearable=False,
                        searchable=True,
                    ),
                ],
            ),
            html.Div(
                style={"minWidth": "220px", "flexGrow": 1},
                children=[
                    html.Label("Maximum hop distance", htmlFor="depth-slider"),
                    dcc.Slider(
                        id="depth-slider",
                        min=0,
                        max=default_max_depth,
                        value=default_slider_value,
                        step=1,
                        marks=default_marks,
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                ],
            ),
            html.Div(
                id="depth-label",
                style={
                    "fontSize": "0.9rem",
                    "color": "#555",
                    "flexBasis": "100%",
                },
                children=initial_summary,
            ),
        ],
    )

    cytoscape = cyto.Cytoscape(
        id="graph-view",
        stylesheet=caches.stylesheet.stylesheet,
        elements=initial_elements,
        layout={
            "name": "fcose",
            "quality": "proof",
            "animate": True,
            "randomize": False,
            "fit": True,
            "padding": 60,
            "nodeDimensionsIncludeLabels": True,
            "uniformNodeDimensions": False,
            "packComponents": True,
            "nodeRepulsion": 1000,
            "idealEdgeLength": 60,
            "edgeElasticity": 0.45,
            "gravity": 0.25,
            "numIter": 2500,
            "tile": True,
            "tilingPaddingVertical": 12,
            "tilingPaddingHorizontal": 12,
            "gravityRangeCompound": 1.5,
            "gravityCompound": 1.5,
            "gravityRange": 3.8,
            "componentSpacing": 40,
        },
        style={"position": "absolute", "width": "100%", "height": "100%"},
    )

    app.layout = html.Div(
        style={
            "display": "flex",
            "flexDirection": "column",
            "height": "100vh",
            "width": "100vw",
        },
        children=[
            controls,
            dcc.Store(
                id="distance-store",
                data={"entry": default_entry, "distances": default_distances},
            ),
            html.Div(
                style={"flex": 1, "position": "relative"},
                children=[cytoscape],
            ),
        ],
    )

    @app.callback(
        Output("entry-node", "value"),
        Output("graph-view", "tapNodeData"),
        Input("graph-view", "tapNodeData"),
        Input("back-button", "n_clicks"),
        State("entry-node", "value"),
        prevent_initial_call=True,
    )
    def update_entry(
        data: dict[str, Any] | None,
        back_clicks: int | None,
        current: str,
    ):  # type: ignore[override]
        triggered_props = getattr(ctx, "triggered_prop_ids", {}) or {}
        trigger = ctx.triggered_id
        print(f"[DEBUG] update_entry called - trigger: {trigger}, data: {data}")

        graph_tapped = (
            trigger == "graph-view" or "graph-view.tapNodeData" in triggered_props
        )
        if graph_tapped:
            print("[DEBUG] Graph tapped detected")
            if not data:
                print("[DEBUG] No data, preventing update")
                raise PreventUpdate
            target_name = data.get("node_full_name")
            if not target_name:
                clicked_id = data.get("id")
                if clicked_id is None:
                    print("[DEBUG] No clicked_id, preventing update")
                    raise PreventUpdate
                clicked_str = str(clicked_id)
                target_name = caches.node_id_to_name.get(clicked_str)
                if target_name is None:
                    target_name = caches.gif_id_to_node_name.get(clicked_str)
            if target_name is None or target_name == caches.current_entry:
                print(f"[DEBUG] Same target ({target_name}) or None, preventing update")
                raise PreventUpdate

            print(
                f"[DEBUG] Updating entry from {caches.current_entry} to {target_name}"
            )
            caches.history.append(caches.current_entry)
            caches.current_entry = target_name
            caches.ignore_entry_change = True
            return target_name, None  # Reset tapNodeData to enable repeated clicks

        back_clicked = (
            trigger == "back-button" or "back-button.n_clicks" in triggered_props
        )
        if back_clicked:
            print("[DEBUG] Back clicked")
            if not caches.history:
                raise PreventUpdate
            previous = caches.history.pop()
            caches.current_entry = previous
            caches.ignore_entry_change = True
            return previous, None  # Reset tapNodeData

        # No relevant trigger -> keep current value
        print("[DEBUG] No relevant trigger, preventing update")
        raise PreventUpdate

    @app.callback(
        Output("distance-store", "data"),
        Output("depth-slider", "max"),
        Output("depth-slider", "marks"),
        Output("depth-slider", "value"),
        Input("entry-node", "value"),
        State("depth-slider", "value"),
    )
    def update_distances(selected_entry: str, current_depth: int | None):  # type: ignore[override]
        print(
            f"[DEBUG] update_distances called - selected_entry: {selected_entry}, "
            f"current_depth: {current_depth}"
        )
        entry_name = selected_entry or caches.default_entry
        print(
            f"[DEBUG] entry_name: {entry_name}, "
            f"caches.current_entry: {caches.current_entry}"
        )

        if entry_name != caches.current_entry:
            print(f"[DEBUG] Entry changed from {caches.current_entry} to {entry_name}")
            if caches.ignore_entry_change:
                print("[DEBUG] Ignoring entry change flag set")
                caches.ignore_entry_change = False
            else:
                print(f"[DEBUG] Adding {caches.current_entry} to history")
                caches.history.append(caches.current_entry)
            caches.current_entry = entry_name
        else:
            print("[DEBUG] No entry change")

        start_id = caches.node_to_self_gif[entry_name]
        print(f"[DEBUG] Computing distances from start_id: {start_id}")
        distances = _compute_distances(start_id, caches.adjacency)
        max_depth = max(distances.values(), default=0)
        default_depth = 0 if max_depth == 0 else 1
        slider_value = min(
            max_depth,
            default_depth if current_depth is None else current_depth,
        )
        marks = _build_slider_marks(max_depth)
        caches.ignore_entry_change = False

        update_id = f"{entry_name}_{time.time()}"
        print(f"[DEBUG] Returning update_id: {update_id}")
        return (
            {
                "entry": entry_name,
                "distances": distances,
                "update_id": update_id,  # Force update detection
            },
            max_depth,
            marks,
            slider_value,
        )

    @app.callback(
        Output("back-button", "disabled"),
        Input("entry-node", "value"),
    )
    def update_back_button(_: str):  # type: ignore[override]
        return not caches.history

    @app.callback(
        Output("graph-view", "elements"),
        Output("depth-label", "children"),
        Input("distance-store", "data"),
        Input("depth-slider", "value"),
    )
    def update_elements(store: dict[str, Any] | None, depth: int | None):  # type: ignore[override]
        print(f"[DEBUG] update_elements called - store: {store}, depth: {depth}")

        if not store:
            print("[DEBUG] No store data, returning empty")
            return [], "Select an entry node to begin."

        entry_name = store.get("entry", caches.default_entry)
        distances: Mapping[str, int] = store.get("distances", {})
        update_id = store.get("update_id", "unknown")
        max_depth = depth or 0

        print(
            f"[DEBUG] entry_name: {entry_name}, max_depth: {max_depth}, "
            f"update_id: {update_id}"
        )
        print(f"[DEBUG] distances keys count: {len(distances)}")

        included_ids = {
            gif_id for gif_id, distance in distances.items() if distance <= max_depth
        }

        if not included_ids:
            included_ids.add(caches.node_to_self_gif[entry_name])

        print(f"[DEBUG] included_ids count: {len(included_ids)}")
        elements = _build_elements(caches, included_ids, entry_name)
        info = _selection_summary(caches, included_ids, max_depth)
        print(f"[DEBUG] Built {len(elements)} elements, returning info: {info}")
        return elements, info

    app.run(jupyter_height=height or 900)


def visualize_pcb_file(
    pcb_path: Path,
    entry: str | None = None,
    *,
    height: int | None = None,
) -> None:
    """Convenience wrapper that loads a KiCad PCB file and launches the viewer."""

    from atopile.pcb_transformer import load_pcb_graph

    data = load_pcb_graph(pcb_path)
    launch_pcb_graph_viewer(
        data.pcb_node,
        entry=entry,
        title=pcb_path.name,
        height=height,
    )


def build_demo_zone_board() -> tuple[PCBNode, ZoneNode]:
    """Create a small PCB graph containing a copper zone."""

    pcb = PCBNode()
    zone = ZoneNode()
    pcb.add(zone, name="demo_zone")

    zone.net_name.alias_is("GND")
    zone.net_number.alias_is(1)
    zone.uuid.alias_is("demo-zone-uuid")

    settings = zone.settings
    settings.clearance.alias_is(0.2)
    settings.min_thickness.alias_is(0.15)
    settings.thermal_gap.alias_is(0.25)
    settings.thermal_width.alias_is(0.35)
    settings.fill_mode.alias_is("solid")

    layer = zone.layer
    kicad_layer = KicadLayerNode()
    layer.add(kicad_layer, name="kicad")
    kicad_layer.name.value.alias_is("F.Cu")

    # Use the existing polygon from zone.outline (created by d_field)
    # and populate it with geometry children
    temp_polygon = zone.outline
    temp_polygon.uuid.alias_is("demo-outline-uuid")

    # Create arc segments (simplified version of the KiCad polygon)
    arcs = [
        # Arc 1: start -> mid -> end
        {
            "start": (170.877107, 109.697107),
            "mid": (171.093875, 110.021531),
            "end": (171.17, 110.404214),
        },
        # Arc 2:
        {
            "start": (171.17, 113.725786),
            "mid": (171.09388, 114.108469),
            "end": (170.877107, 114.432893),
        },
        # Arc 3:
        {
            "start": (170.433647, 114.876353),
            "mid": (170.109223, 115.093129),
            "end": (169.72654, 115.169246),
        },
        # Arc 4:
        {
            "start": (166.787601, 115.169246),
            "mid": (166.103339, 114.898482),
            "end": (165.789624, 114.232816),
        },
    ]

    # Create straight line points
    straight_points = [
        (165.522023, 110.031753),
        (165.52, 109.968183),
        (165.52, 109.78),
    ]

    # More arcs
    more_arcs = [
        {
            "start": (166.387107, 108.912893),
            "mid": (166.71153, 108.69612),
            "end": (167.094214, 108.62),
        },
        {
            "start": (169.385786, 108.62),
            "mid": (169.768472, 108.696116),
            "end": (170.092893, 108.912893),
        },
    ]

    # Add all arcs as ArcNode children
    arc_nodes = []
    for i, arc_data in enumerate(arcs + more_arcs):
        arc_node = ArcNode()
        arc_node.start.x.alias_is(arc_data["start"][0])
        arc_node.start.y.alias_is(arc_data["start"][1])
        arc_node.center.x.alias_is(arc_data["mid"][0])
        arc_node.center.y.alias_is(arc_data["mid"][1])
        arc_node.end.x.alias_is(arc_data["end"][0])
        arc_node.end.y.alias_is(arc_data["end"][1])
        arc_node.width.alias_is(0.0)  # Polygon arcs have no stroke width
        temp_polygon.add(arc_node, name=f"arc_{i}")
        arc_nodes.append(arc_node)

    # Add straight line points as XYRNode children
    point_nodes = []
    for idx, (x, y) in enumerate(straight_points):
        point_node = XYRNode()
        point_node.x.alias_is(x)
        point_node.y.alias_is(y)
        temp_polygon.add(point_node, name=f"point_{idx}")
        point_nodes.append(point_node)

    # Connect elements in sequence to form the polygon ring
    # This demonstrates a complex polygon with mixed arcs and straight segments
    all_elements = arc_nodes[:4] + point_nodes + arc_nodes[4:]
    for idx, element in enumerate(all_elements):
        next_element = all_elements[(idx + 1) % len(all_elements)]
        element.connect(next_element)

    # Note: temp_polygon is already zone.outline, so no assignment needed

    # Add some standalone examples using the working helper functions
    from faebryk.core.pcbgraph import (
        KicadLayer,
        new_arc,
        new_circle,
        new_line,
        new_via,
    )

    # These should work since the helpers work
    demo_line = new_line(150.0, 100.0, 160.0, 100.0, 0.2, KicadLayer.F_Cu)
    demo_arc = new_arc(
        160.0, 100.0, 165.0, 105.0, 170.0, 100.0, 0.2, KicadLayer.F_SilkS
    )
    demo_circle = new_circle(175.0, 100.0, 2.0, KicadLayer.F_SilkS)
    demo_via = new_via(180.0, 100.0, 0.3, 0.6)

    pcb.add(demo_line, name="demo_line")
    pcb.add(demo_arc, name="demo_arc")
    pcb.add(demo_circle, name="demo_circle")
    pcb.add(demo_via, name="demo_via")

    return pcb, zone


def main(argv: Sequence[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect the Faebryk PCB graph for a KiCad layout.",
    )
    parser.add_argument(
        "pcb",
        type=Path,
        nargs="?",
        help="Path to the .kicad_pcb file",
    )
    parser.add_argument(
        "--entry",
        type=str,
        help="Full or partial name of the entry node to focus on",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Optional viewport height (pixels) when running inside notebooks",
    )
    parser.add_argument(
        "--demo-zone",
        action="store_true",
        help="Launch a synthetic example containing a copper zone",
    )
    parser.add_argument(
        "--dump-elements",
        action="store_true",
        help="Print generated Cytoscape elements instead of starting the UI",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Limit dump mode to this hop distance",
    )

    args = parser.parse_args(argv)

    target_graph: Graph | Node
    entry_target: Node | str | None = args.entry

    if args.demo_zone:
        target_graph, zone = build_demo_zone_board()
        if entry_target is None:
            entry_target = target_graph  # Start from PCB root to see all nodes
    elif args.pcb is not None:
        target_graph = args.pcb
    else:
        parser.error("Provide a PCB file path or --demo-zone")

    if args.dump_elements:
        if isinstance(target_graph, Path):
            from atopile.pcb_transformer import load_pcb_graph

            pcb_node = load_pcb_graph(target_graph).pcb_node
            caches = _prepare_caches(pcb_node, entry_target)
        else:
            caches = _prepare_caches(target_graph, entry_target)

        entry_name = (
            entry_target if isinstance(entry_target, str) else caches.default_entry
        )
        start_id = caches.node_to_self_gif[entry_name]
        distances = _compute_distances(start_id, caches.adjacency)
        max_depth = (
            args.max_depth
            if args.max_depth is not None
            else max(distances.values(), default=0)
        )
        included_ids = {
            gif_id for gif_id, depth in distances.items() if depth <= max_depth
        }
        elements = _build_elements(caches, included_ids, entry_name)
        print(f"Entry: {entry_name}")
        print(f"Interfaces: {len(included_ids)} · Elements: {len(elements)}")
        for element in elements:
            print(element)
        return

    if isinstance(target_graph, Path):
        visualize_pcb_file(target_graph, entry=args.entry, height=args.height)
    else:
        launch_pcb_graph_viewer(
            target_graph,
            entry=entry_target,
            height=args.height,
            title="Demo Zone Board" if args.demo_zone else None,
        )


if __name__ == "__main__":  # pragma: no cover - manual tool entry point
    main()
