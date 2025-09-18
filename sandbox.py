import math
from collections import deque
from typing import cast

import matplotlib.patches as patches
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.widgets import Button

import faebryk.library._F as F
from faebryk.core.graphinterface import GraphInterface, GraphInterfaceReference
from faebryk.core.link import LinkPointer
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.core.parameter import Parameter
from faebryk.libs.library import L
from faebryk.libs.units import P

# class Attribute[T = str | int | float]:
#     def __init__(self, value: T | None) -> None:
#         self.name: str | None = None
#         self.value = value

type_sentinel = Node()


class NNode(Node):
    def __init__(self):
        # Initialize as a regular Node
        super().__init__()
        # Add the required GraphInterfaces as fields
        # self.add(GraphInterface(), name="rules")
        # self.add(GraphInterface(), name="instances")
        # self.add(GraphInterface(), name="type")

    rules: GraphInterface
    instances: GraphInterface
    type: GraphInterface
    connections: GraphInterface


class NodeType(NNode):
    def __init__(self, identifier: str):
        super().__init__()
        self.identifier = identifier

    rules: GraphInterface
    instances: GraphInterface
    type: GraphInterface

    def __postinit__(self):
        self.type.connect(type_sentinel.self_gif)
        pass
        # self.add(GraphInterface(), "rules")

    def execute(self) -> NNode:
        node = NNode()
        node.type.connect(self.self_gif)
        for rule in self.rules.get_connected_nodes([Rule]):
            assert isinstance(rule, Rule)
            rule.execute(node)

        return node


type_make_child = NodeType("MakeChild")
type_trait = NodeType("Trait")
type_parameter = NodeType("Parameter")


class Rule(NNode):
    def execute(self, node: NNode) -> None:
        pass


class FieldDeclaration(Rule):
    def __init__(self, identifier: str | None, nodetype: type[NNode]):
        super().__init__()
        self.identifier = identifier
        self.nodetype = nodetype

    def execute(self, node: NNode) -> None:
        super().execute(node)
        obj = self.nodetype()

        node.add(obj, name=self.identifier)


class MakeChild(Rule):
    def __init__(self, identifier: str | None, nodetype: NodeType):
        super().__init__()
        self.identifier = identifier
        self.nodetype = nodetype

    def __postinit__(self):
        self.type.connect(type_make_child.self_gif)

    def execute(self, node: NNode) -> None:
        super().execute(node)
        obj = self.nodetype.execute()
        # obj.type.connect(self.nodetype.self_gif)

        node.add(obj, name=self.identifier)


# class FieldReference(NNode):
#     def resolve[T: NNode](self, type: type[T], node: "NNode") -> T: ...


# class _GraphInterfaceReference[T: NNode](GraphInterfaceReference):
#     def __init__(self, *ref: T):
#         super().__init__()
# self.connect([r.self_gif for r in ref], LinkPointer())

# @property
# def reference(self) -> T:
#     return cast(T, self.get_referenced_gif().node)

# @property
# def references(self) -> list[T]:
#     return [cast(T, r.node) for r in self.get_gif_edges()]


# class Connect(Rule):
#     def __init__(self, *objects: list[FieldReference]):
#         super().__init__()
#         self.objects = objects
#         self.interfaces = _GraphInterfaceReference(*objects)

#     def execute(self, node: NNode):
#         super().execute(node)
#         interfaces_and_bridges = [
#             ref.resolve(ModuleOrInterface, node) for ref in self.interfaces.references
#         ]
#         if not interfaces_and_bridges:
#             return
#         start = interfaces_and_bridges[0]
#         bridges = []
#         end = []
#         for i, b in enumerate(interfaces_and_bridges[1:]):
#             if not isinstance(b, Module):
#                 end = interfaces_and_bridges[i + 1 :]
#             # if not b.has_trait(can_bridge):
#             #    raise
#             bridges.append(b)

#         start.connect_via(bridges, *end)


## CAN BRIDGE TYPE ##
type_can_bridge = NodeType("CanBridge")
type_can_bridge.rules.connect(
    MakeChild(identifier="trait", nodetype=type_trait).self_gif
)
# TODO: add in and out for this trait so it can be connected to other interfaces
# type_can_bridge.rules.connect(MakeChild)

## ELECTRICAL TYPE ##
type_electrical = NodeType("Electrical")

### RESISTOR TYPE ###
type_resistor = NodeType("Resistor")
type_resistor.rules.connect(MakeChild("p1", type_electrical).self_gif)
type_resistor.rules.connect(MakeChild("p2", type_electrical).self_gif)
type_resistor.rules.connect(MakeChild("resistance", type_parameter).self_gif)
type_resistor.rules.connect(MakeChild("max_power", type_parameter).self_gif)
type_resistor.rules.connect(MakeChild("max_voltage", type_parameter).self_gif)
type_resistor.rules.connect(
    MakeChild(identifier="can_bridge", nodetype=type_can_bridge).self_gif
)

## CAPACITOR TYPE ###
type_capacitor = NodeType("Capacitor")
type_capacitor.rules.connect(MakeChild("p1", type_electrical).self_gif)
type_capacitor.rules.connect(MakeChild("p2", type_electrical).self_gif)
type_capacitor.rules.connect(MakeChild("capacitance", type_parameter).self_gif)
type_capacitor.rules.connect(MakeChild("max_voltage", type_parameter).self_gif)
type_capacitor.rules.connect(MakeChild("can_bridge", type_can_bridge).self_gif)

## RC FILTER TYPE ##
type_rc_filter = NodeType("RCFilter")
type_rc_filter.rules.connect(MakeChild("in_", type_electrical).self_gif)
type_rc_filter.rules.connect(MakeChild("out", type_electrical).self_gif)
type_rc_filter.rules.connect(MakeChild("resistor", type_resistor).self_gif)
type_rc_filter.rules.connect(MakeChild("capacitor", type_capacitor).self_gif)
# type_rc_filter.rules.connect(
#     Connect(
#         [type_rc_filter.connections, type_resistor.self_gif, type_capacitor.self_gif]
#     )
# )


# print(dummy_node.children.get_children())

# gifs = resistor.self_gif.get_gif_edges()
# print([gif.name for gif in gifs])

# node_type = NodeType("Resistor")
# children = node_type.children.get_children()
# gifs = node_type.self_gif.get_gif_edges()
# print([gif.name for gif in gifs])
# node_type.instances.connect(resistor.type)

# resistor_instance = type_resistor.execute()
# capacitor_instance = type_capacitor.execute()
rc_filter_instance = type_rc_filter.execute()


# --------------- Visualization ---------------


def _collect_from(
    start: Node,
    graph=None,
) -> tuple[list[Node], list[tuple[GraphInterface, GraphInterface]]]:
    """
    Traverse graph from a starting hypernode by following children edges.
    Returns discovered hypernodes and interface-level edges.
    """
    seen_nodes: set[Node] = set()
    nodes: list[Node] = []
    iface_edges: list[tuple[GraphInterface, GraphInterface]] = []
    seen_if_ids: set[tuple[int, int]] = set()

    q: deque[Node] = deque([start])
    # defer graph fetch until needed
    _graph = graph or start.get_graph()

    while q:
        n = q.popleft()
        if n in seen_nodes:
            continue
        seen_nodes.add(n)
        nodes.append(n)

        # enqueue children (hypernodes)
        for child in n.children.get_children():
            q.append(child)

        # collect ALL interfaces owned by this node by scanning the graph
        all_gifs = [gif for gif in _graph.get_gifs() if gif.node is n]

        # connect self to owned interfaces (if not already)
        for gif in all_gifs:
            key = (id(n.self_gif), id(gif))
            if key not in seen_if_ids:
                seen_if_ids.add(key)
                iface_edges.append((n.self_gif, gif))

        # from every owned interface, follow connections
        for lg in all_gifs:
            for other in lg.get_gif_edges():
                key = (id(lg), id(other))
                if key not in seen_if_ids:
                    seen_if_ids.add(key)
                    iface_edges.append((lg, other))
                # enqueue the node owning the connected interface
                q.append(other.node)

    return nodes, iface_edges


def _interfaces_of(node: Node, graph=None) -> list[GraphInterface]:
    # Return all GIFs owned by the node (including self)
    _graph = graph or node.get_graph()
    gifs = [gif for gif in _graph.get_gifs() if gif.node is node]
    if node.self_gif not in gifs:
        gifs.append(node.self_gif)
    return gifs


class InteractiveTypeGraphVisualizer:
    def __init__(self, root: Node, figsize: tuple[int, int] = (20, 14)):
        self.root = root
        self.graph = root.get_graph()
        self.nodes, self.iface_edges = _collect_from(root, self.graph)

        # Build data structures
        self._build_data_structures()
        self._calculate_layout()

        # Create figure and axes
        self.fig, self.ax = plt.subplots(figsize=figsize)
        if hasattr(self.fig.canvas, "manager") and self.fig.canvas.manager:
            self.fig.canvas.manager.set_window_title(
                "Interactive Type Graph Visualizer"
            )

        # Store original axis limits for reset
        self.original_xlim = None
        self.original_ylim = None

        # Create UI elements
        self._create_ui()

        # Draw initial graph
        self._draw_graph()

        # Set up interactivity
        self._setup_interactivity()

    def _build_data_structures(self):
        # Build mapping: interface -> owning hypernode
        self.iface_to_node: dict[GraphInterface, Node] = {}
        for n in self.nodes:
            for gif in _interfaces_of(n, self.graph):
                self.iface_to_node[gif] = n

        # Build hypernode adjacency from interface edges
        self.hn_adj: dict[Node, set[Node]] = {n: set() for n in self.nodes}
        for a, b in self.iface_edges:
            na = self.iface_to_node.get(a)
            nb = self.iface_to_node.get(b)
            if na is None or nb is None or na is nb:
                continue
            self.hn_adj[na].add(nb)
            self.hn_adj[nb].add(na)

    def _calculate_layout(self):
        # Assign canonical levels by category
        # 0: sentinel, 1: NodeTypes, 2: Rules, 3: Instances, 4: Children of Instances
        def _is_nodetype(n: Node) -> bool:
            try:
                return isinstance(n, NodeType)
            except Exception:
                return False

        def _is_rule(n: Node) -> bool:
            try:
                return isinstance(n, Rule)
            except Exception:
                return False

        def _is_instance(n: Node) -> bool:
            # instance: not NodeType/Rule and has a type connection to a NodeType
            if _is_nodetype(n) or _is_rule(n):
                return False
            try:
                type_edges = (
                    n.type.get_gif_edges() if hasattr(n, "type") and n.type else []
                )
            except Exception:
                type_edges = []
            return any(_is_nodetype(g.node) for g in type_edges)

        # precompute instance set
        instance_set: set[Node] = {n for n in self.nodes if _is_instance(n)}

        def _is_child_instance(n: Node) -> bool:
            if n in instance_set:
                # child instance should not include the parent instance itself
                # Determine if parent is an instance
                try:
                    parent = n.get_parent()
                except Exception:
                    parent = None
                if parent is None:
                    return False
                pnode, _ = parent
                return pnode in instance_set
            return False

        levels: dict[int, list[Node]] = {}
        for n in self.nodes:
            if n is self.root:
                l = 0
            elif _is_nodetype(n):
                l = 1
            elif _is_rule(n):
                l = 2
            elif _is_child_instance(n):
                l = 4
            elif _is_instance(n):
                l = 3
            else:
                # Unclassified: place between rules and instances
                l = 3
            levels.setdefault(l, []).append(n)

        # Base grid positions per level with increased spacing
        self.hn_pos: dict[Node, tuple[float, float]] = {}
        level_gap_y = 50.0  # Increased vertical spacing
        base_spacing_x = 60.0  # Increased horizontal spacing

        # Special handling for instance grouping
        type_to_instances = {}
        instance_to_children = {}
        for n in self.nodes:
            # Check if this node is an instance of a type
            if hasattr(n, "type") and n.type:
                # Find the type this instance belongs to
                type_connections = n.type.get_gif_edges()
                for type_gif in type_connections:
                    type_node = type_gif.node
                    if isinstance(type_node, NodeType):
                        if type_node not in type_to_instances:
                            type_to_instances[type_node] = []
                        type_to_instances[type_node].append(n)
        # Map instances to their child instances
        for inst in list(instance_set):
            try:
                ch = inst.children.get_children()
            except Exception:
                ch = []
            # Only keep children that are also in our traversal set
            ch = [c for c in ch if c in self.nodes]
            if ch:
                instance_to_children[inst] = ch

        for l in sorted(levels.keys()):
            layer = levels[l]
            k = max(1, len(layer))
            span = base_spacing_x * (k - 1)
            xs = [(-span / 2.0) + i * base_spacing_x for i in range(k)]
            y = -l * level_gap_y
            for i, n in enumerate(layer):
                self.hn_pos[n] = (xs[i], y)

        # Group instances near their type parents
        instance_offset_distance = 40.0  # Distance from parent type
        for type_node, instances in type_to_instances.items():
            if type_node in self.hn_pos and instances:
                type_x, type_y = self.hn_pos[type_node]

                # Arrange instances in a circle around their type
                num_instances = len(instances)
                for i, instance in enumerate(instances):
                    if instance in self.hn_pos:
                        angle = 2 * math.pi * i / num_instances
                        offset_x = instance_offset_distance * math.cos(angle)
                        offset_y = instance_offset_distance * math.sin(angle)

                        # Place instance near its type, but maintain level structure
                        instance_x, instance_y = self.hn_pos[instance]
                        self.hn_pos[instance] = (
                            type_x + offset_x,
                            instance_y,  # Keep original y-level
                        )

        # Pull instances toward the centroid of their child instances (to be near children)
        child_alpha = 0.7
        for inst, ch in instance_to_children.items():
            if inst not in self.hn_pos:
                continue
            xs = [self.hn_pos[c][0] for c in ch if c in self.hn_pos]
            if not xs:
                continue
            mean_x = sum(xs) / len(xs)
            x, y = self.hn_pos[inst]
            self.hn_pos[inst] = ((1 - child_alpha) * x + child_alpha * mean_x, y)

        # Pull remaining nodes toward their parents (non-instance relationships)
        alpha = 0.6  # Increased attraction strength
        for l in sorted(levels.keys()):
            if l == 0:
                continue
            for n in levels[l]:
                # Skip instances that are already positioned near their types
                is_positioned_instance = any(
                    n in instances for instances in type_to_instances.values()
                )
                if is_positioned_instance:
                    continue

                parents = [
                    p for p in self.hn_adj.get(n, set()) if level.get(p) == l - 1
                ]
                if not parents:
                    continue
                mean_x = sum(self.hn_pos[p][0] for p in parents) / len(parents)
                x, y = self.hn_pos[n]
                self.hn_pos[n] = ((1 - alpha) * x + alpha * mean_x, y)

        # Apply collision detection and node separation
        self._separate_overlapping_nodes()

        # Place interfaces within each hypernode in a smaller circle
        self.pos: dict[GraphInterface, tuple[float, float]] = {}
        self.r_if_by_node: dict[Node, float] = {}
        for n in self.nodes:
            center = self.hn_pos[n]
            ifaces = _interfaces_of(n, self.graph)
            k = max(1, len(ifaces))
            r_if_local = max(6.0, 1.2 * k)  # Increased interface radius
            self.r_if_by_node[n] = r_if_local
            for j, gif in enumerate(ifaces):
                a = 2 * math.pi * j / k
                self.pos[gif] = (
                    center[0] + r_if_local * math.cos(a),
                    center[1] + r_if_local * math.sin(a),
                )

    def _separate_overlapping_nodes(self):
        """Separate overlapping nodes using force-based positioning"""
        min_distance = 45.0  # Minimum distance between node centers
        max_iterations = 50
        force_strength = 0.1

        for iteration in range(max_iterations):
            forces = {node: (0.0, 0.0) for node in self.hn_pos.keys()}

            # Calculate repulsive forces between all pairs of nodes
            nodes_list = list(self.hn_pos.keys())
            for i, node1 in enumerate(nodes_list):
                for node2 in nodes_list[i + 1 :]:
                    x1, y1 = self.hn_pos[node1]
                    x2, y2 = self.hn_pos[node2]

                    dx = x2 - x1
                    dy = y2 - y1
                    distance = math.sqrt(dx * dx + dy * dy)

                    if distance < min_distance and distance > 0:
                        # Calculate repulsive force
                        force_magnitude = (min_distance - distance) / distance
                        fx = -dx * force_magnitude * force_strength
                        fy = -dy * force_magnitude * force_strength

                        # Apply forces
                        forces[node1] = (forces[node1][0] + fx, forces[node1][1] + fy)
                        forces[node2] = (forces[node2][0] - fx, forces[node2][1] - fy)

            # Apply forces to update positions
            total_movement = 0.0
            for node, (fx, fy) in forces.items():
                x, y = self.hn_pos[node]
                new_x = x + fx
                new_y = y + fy
                self.hn_pos[node] = (new_x, new_y)
                total_movement += abs(fx) + abs(fy)

            # Stop if system has stabilized
            if total_movement < 0.1:
                break

    def _node_label(self, n: Node) -> str:
        return (
            getattr(n, "identifier", None)
            or getattr(n, "name", None)
            or n.get_name(True)
            or n.__class__.__name__
        )

    def _create_ui(self):
        # Create control panel
        plt.subplots_adjust(bottom=0.15)

        # Navigation buttons
        ax_reset = plt.axes((0.02, 0.02, 0.08, 0.04))
        self.btn_reset = Button(ax_reset, "Reset View")

        ax_zoom_in = plt.axes((0.12, 0.02, 0.08, 0.04))
        self.btn_zoom_in = Button(ax_zoom_in, "Zoom In")

        ax_zoom_out = plt.axes((0.22, 0.02, 0.08, 0.04))
        self.btn_zoom_out = Button(ax_zoom_out, "Zoom Out")

        ax_focus_root = plt.axes((0.32, 0.02, 0.08, 0.04))
        self.btn_focus_root = Button(ax_focus_root, "Focus Root")

        ax_focus_types = plt.axes((0.42, 0.02, 0.08, 0.04))
        self.btn_focus_types = Button(ax_focus_types, "Focus Types")

        ax_focus_rules = plt.axes((0.52, 0.02, 0.08, 0.04))
        self.btn_focus_rules = Button(ax_focus_rules, "Focus Rules")

        ax_focus_instances = plt.axes((0.62, 0.02, 0.10, 0.04))
        self.btn_focus_instances = Button(ax_focus_instances, "Focus Instances")

        # Info text
        self.info_text = self.ax.text(
            0.02,
            0.98,
            "Controls: Mouse wheel = zoom, Click+drag = pan, Double-click node = focus",
            transform=self.ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
        )

    def _setup_interactivity(self):
        # Connect event handlers
        self.btn_reset.on_clicked(self._on_reset_view)
        self.btn_zoom_in.on_clicked(self._on_zoom_in)
        self.btn_zoom_out.on_clicked(self._on_zoom_out)
        self.btn_focus_root.on_clicked(self._on_focus_root)
        self.btn_focus_types.on_clicked(self._on_focus_types)
        self.btn_focus_rules.on_clicked(self._on_focus_rules)
        self.btn_focus_instances.on_clicked(self._on_focus_instances)

        # Mouse events
        self.fig.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.fig.canvas.mpl_connect("button_press_event", self._on_button_press)
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_mouse_motion)
        self.fig.canvas.mpl_connect("button_release_event", self._on_button_release)

        # Panning state
        self.panning = False
        self.pan_start = None

    def _draw_graph(self):
        self.ax.clear()

        # Draw hypernodes as big circles
        for n in self.nodes:
            cx, cy = self.hn_pos[n]
            r_draw = self.r_if_by_node.get(n, 2.0) * 1.9

            # Outline color by type: NodeType -> black, Rule -> red, Instances/others -> blue
            try:
                is_nodetype = isinstance(n, NodeType)
            except Exception:
                is_nodetype = False
            try:
                is_rule = isinstance(n, Rule)
            except Exception:
                is_rule = False

            if is_nodetype:
                ec_color = "#000000"
                face_color = "#e8f0fe"
            elif is_rule:
                ec_color = "#d33"
                face_color = "#ffe8e8"
            else:
                ec_color = "#1f77b4"
                face_color = "#e8f4ff"

            circle = patches.Circle(
                (cx, cy),
                r_draw,
                color=face_color,
                ec=ec_color,
                lw=1.8,
                alpha=0.7,
                picker=True,
            )
            self.ax.add_patch(circle)

            label_main = self._node_label(n)
            label_type = n.__class__.__name__

            # main name slightly above center, type slightly below
            main_text = self.ax.text(
                cx,
                cy + 0.25,
                label_main,
                ha="center",
                va="center",
                fontsize=8,
                weight="bold",
                zorder=20,
            )
            type_text = self.ax.text(
                cx,
                cy - 0.25,
                f"[{label_type}]",
                ha="center",
                va="center",
                fontsize=6,
                color="#555555",
                style="italic",
                zorder=20,
            )

            # Add subtle shadow effect
            main_text.set_path_effects(
                [path_effects.withStroke(linewidth=3, foreground="white")]
            )
            type_text.set_path_effects(
                [path_effects.withStroke(linewidth=2, foreground="white")]
            )

        # Draw interface edges with color by connection type
        for a, b in self.iface_edges:
            pa = self.pos.get(a)
            pb = self.pos.get(b)
            if pa is None or pb is None:
                continue

            edge_color = "#7a7a7a"
            edge_width = 1.3
            edge_alpha = 0.7

            try:
                if a.name == "rules" or b.name == "rules":
                    edge_color = "#d33"  # rule connections
                    edge_width = 1.5
                elif a.name == "type" or b.name == "type":
                    edge_color = "#2ca02c"  # type connections
                    edge_width = 1.5
            except Exception:
                pass

            self.ax.plot(
                [pa[0], pb[0]],
                [pa[1], pb[1]],
                color=edge_color,
                alpha=edge_alpha,
                linewidth=edge_width,
            )

        # Draw interfaces as nodes
        xs = [xy[0] for xy in self.pos.values()]
        ys = [xy[1] for xy in self.pos.values()]
        self.ax.scatter(
            xs,
            ys,
            s=450,
            c="#ffe8cc",
            edgecolors="#cc7a00",
            linewidths=1.5,
            picker=True,
            zorder=10,
        )

        # Label interfaces with their names
        for gif, (x, y) in self.pos.items():
            owner = self.iface_to_node.get(gif)
            if owner is not None and gif is owner.self_gif:
                label = f"{gif.name}:{self._node_label(owner)}"
            else:
                label = gif.name

            text = self.ax.text(
                x,
                y,
                label,
                fontsize=7,
                ha="center",
                va="center",
                weight="bold",
                zorder=25,
            )
            text.set_path_effects(
                [path_effects.withStroke(linewidth=2, foreground="white")]
            )

        # Set aspect ratio and axis properties
        self.ax.set_aspect("equal", adjustable="datalim")
        self.ax.axis("off")

        # Calculate proper limits to ensure all content is visible
        if hasattr(self, "hn_pos") and self.hn_pos:
            # Get bounds of all nodes including their radii
            xs, ys = zip(*self.hn_pos.values())
            radii = [self.r_if_by_node.get(n, 2.0) * 1.9 for n in self.hn_pos.keys()]

            min_x = min(x - r for x, r in zip(xs, radii))
            max_x = max(x + r for x, r in zip(xs, radii))
            min_y = min(y - r for y, r in zip(ys, radii))
            max_y = max(y + r for y, r in zip(ys, radii))

            # Add padding
            padding = 5.0
            x_range = max_x - min_x + 2 * padding
            y_range = max_y - min_y + 2 * padding

            # Center the view
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2

            self.ax.set_xlim(center_x - x_range / 2, center_x + x_range / 2)
            self.ax.set_ylim(center_y - y_range / 2, center_y + y_range / 2)

        # Store original limits if not set
        if self.original_xlim is None:
            self.original_xlim = self.ax.get_xlim()
            self.original_ylim = self.ax.get_ylim()

        # Re-add info text
        self.info_text = self.ax.text(
            0.02,
            0.98,
            "Controls: Mouse wheel = zoom, Click+drag = pan, Double-click node = focus",
            transform=self.ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
        )

        self.fig.canvas.draw_idle()

    def _on_scroll(self, event):
        """Handle mouse wheel zoom"""
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return

        # Get current axis limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()

        # Calculate zoom factor (smaller steps for more control, reversed direction)
        zoom_factor = 1 / 1.15 if event.button == "up" else 1.15

        # Get mouse position in data coordinates
        mouse_x, mouse_y = event.xdata, event.ydata

        # Calculate current center and ranges
        current_x_range = xlim[1] - xlim[0]
        current_y_range = ylim[1] - ylim[0]

        # Calculate new ranges
        new_x_range = current_x_range * zoom_factor
        new_y_range = current_y_range * zoom_factor

        # Calculate how much to shift the view to keep mouse position stable
        x_shift = (mouse_x - xlim[0]) / current_x_range
        y_shift = (mouse_y - ylim[0]) / current_y_range

        # Calculate new limits
        new_x_min = mouse_x - new_x_range * x_shift
        new_x_max = new_x_min + new_x_range
        new_y_min = mouse_y - new_y_range * y_shift
        new_y_max = new_y_min + new_y_range

        self.ax.set_xlim(new_x_min, new_x_max)
        self.ax.set_ylim(new_y_min, new_y_max)

        # Force redraw
        self.fig.canvas.draw_idle()

    def _on_button_press(self, event):
        """Handle mouse button press"""
        if event.inaxes != self.ax:
            return

        if event.button == 1:  # Left click
            if event.dblclick:
                # Double click - focus on nearest node
                self._focus_on_point(event.xdata, event.ydata)
            else:
                # Single click - start panning
                self.panning = True
                self.pan_start = (event.xdata, event.ydata)

    def _on_mouse_motion(self, event):
        """Handle mouse motion for panning"""
        if not self.panning or event.inaxes != self.ax or self.pan_start is None:
            return

        if event.xdata is None or event.ydata is None:
            return

        dx = event.xdata - self.pan_start[0]
        dy = event.ydata - self.pan_start[1]

        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()

        self.ax.set_xlim(xlim[0] - dx, xlim[1] - dx)
        self.ax.set_ylim(ylim[0] - dy, ylim[1] - dy)

        # Use draw_idle for smoother interaction
        self.fig.canvas.draw_idle()

    def _on_button_release(self, event):
        """Handle mouse button release"""
        if event.button == 1:  # Left click
            self.panning = False
            self.pan_start = None

    def _focus_on_point(self, x, y):
        """Focus on the nearest node to the given point"""
        min_dist = float("inf")
        closest_node = None

        for node, (nx, ny) in self.hn_pos.items():
            dist = math.sqrt((x - nx) ** 2 + (y - ny) ** 2)
            if dist < min_dist:
                min_dist = dist
                closest_node = node

        if closest_node:
            self._focus_on_node(closest_node)

    def _focus_on_node(self, node):
        """Focus the view on a specific node"""
        if node not in self.hn_pos:
            return

        cx, cy = self.hn_pos[node]
        r_draw = self.r_if_by_node.get(node, 2.0) * 3  # Extra padding

        self.ax.set_xlim(cx - r_draw, cx + r_draw)
        self.ax.set_ylim(cy - r_draw, cy + r_draw)
        self.fig.canvas.draw_idle()

    def _focus_on_nodes(self, nodes):
        """Focus the view on a collection of nodes"""
        if not nodes:
            return

        positions = [self.hn_pos[n] for n in nodes if n in self.hn_pos]
        if not positions:
            return

        xs, ys = zip(*positions)
        margin = 15  # Add some margin

        self.ax.set_xlim(min(xs) - margin, max(xs) + margin)
        self.ax.set_ylim(min(ys) - margin, max(ys) + margin)
        self.fig.canvas.draw_idle()

    # Button event handlers
    def _on_reset_view(self, event):
        """Reset view to original"""
        if self.original_xlim and self.original_ylim:
            self.ax.set_xlim(self.original_xlim)
            self.ax.set_ylim(self.original_ylim)
            self.fig.canvas.draw_idle()

    def _on_zoom_in(self, event):
        """Zoom in by 20%"""
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()

        center_x = (xlim[0] + xlim[1]) / 2
        center_y = (ylim[0] + ylim[1]) / 2

        x_range = (xlim[1] - xlim[0]) * 0.8
        y_range = (ylim[1] - ylim[0]) * 0.8

        self.ax.set_xlim(center_x - x_range / 2, center_x + x_range / 2)
        self.ax.set_ylim(center_y - y_range / 2, center_y + y_range / 2)
        self.fig.canvas.draw_idle()

    def _on_zoom_out(self, event):
        """Zoom out by 25%"""
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()

        center_x = (xlim[0] + xlim[1]) / 2
        center_y = (ylim[0] + ylim[1]) / 2

        x_range = (xlim[1] - xlim[0]) * 1.25
        y_range = (ylim[1] - ylim[0]) * 1.25

        self.ax.set_xlim(center_x - x_range / 2, center_x + x_range / 2)
        self.ax.set_ylim(center_y - y_range / 2, center_y + y_range / 2)
        self.fig.canvas.draw_idle()

    def _on_focus_root(self, event):
        """Focus on root node"""
        self._focus_on_node(self.root)

    def _on_focus_types(self, event):
        """Focus on NodeType nodes"""
        type_nodes = [n for n in self.nodes if isinstance(n, NodeType)]
        self._focus_on_nodes(type_nodes)

    def _on_focus_rules(self, event):
        """Focus on Rule nodes"""
        rule_nodes = [n for n in self.nodes if isinstance(n, Rule)]
        self._focus_on_nodes(rule_nodes)

    def _on_focus_instances(self, event):
        """Focus on instance nodes (non-NodeType, non-Rule)"""
        instance_nodes = [
            n
            for n in self.nodes
            if not isinstance(n, NodeType) and not isinstance(n, Rule)
        ]
        self._focus_on_nodes(instance_nodes)

    def show(self):
        """Display the interactive visualization"""
        # Adjust layout to prevent clipping
        try:
            plt.tight_layout(pad=1.0)
        except Exception:
            # Fallback if tight_layout fails
            pass

        # Ensure all content is visible by adjusting margins if needed
        plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.15)
        plt.show()


def visualize_type_graph(root: Node, figsize: tuple[int, int] = (20, 14)) -> None:
    """Create and display an interactive type graph visualization"""
    visualizer = InteractiveTypeGraphVisualizer(root, figsize)
    visualizer.show()


# Start visualization from type_sentinel
visualize_type_graph(type_sentinel)

print(type_resistor.rules.get_connected_nodes([Node]))
