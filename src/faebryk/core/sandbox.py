import math
from collections import deque

import matplotlib.patches as patches
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

import faebryk.library._F as F

# from faebryk.library.Resistor import Resistor
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.node import Node
from faebryk.core.type import Type_ImplementsType, _Node

# Import concrete Modules to trigger Node.__init_subclass__ registration
# and autogeneration of MakeChild/ChildReference nodes

# OLD EXAMLES --------------------------------------------------------------------------
# class Attribute[T = str | int | float]:
#     def __init__(self, value: T | None) -> None:
#         self.name: str | None = None
#         self.value = value

# ## CAN BRIDGE TYPE ##
# type_can_bridge = NodeType("CanBridge")
# trait_ref = ChildRef("trait").with_nodetype(type_trait)
# trait_rule = MakeChild().with_child_reference(trait_ref)
# type_can_bridge.add(trait_rule, name=trait_ref._identifier)

# ## ELECTRICAL TYPE ##
# type_electrical = NodeType("Electrical")

# ### RESISTOR TYPE ###
# type_resistor = NodeType("Resistor")
# p1_ref = ChildRef("p1").with_nodetype(type_electrical)
# p1_rule = MakeChild().with_child_reference(p1_ref)
# type_resistor.add(p1_rule, name=p1_ref._identifier)

# p2_ref = ChildRef("p2").with_nodetype(type_electrical)
# p2_rule = MakeChild().with_child_reference(p2_ref)
# type_resistor.add(p2_rule, name=p2_ref._identifier)

# resistance_ref = ChildRef("resistance").with_nodetype(type_parameter)
# resistance_rule = MakeChild().with_child_reference(resistance_ref)
# type_resistor.add(resistance_rule, name=resistance_ref._identifier)

# max_power_ref = ChildRef("max_power").with_nodetype(type_parameter)
# max_power_rule = MakeChild().with_child_reference(max_power_ref)
# type_resistor.add(max_power_rule, name=max_power_ref._identifier)

# max_voltage_ref = ChildRef("max_voltage").with_nodetype(type_parameter)
# max_voltage_rule = MakeChild().with_child_reference(max_voltage_ref)
# type_resistor.add(max_voltage_rule, name=max_voltage_ref._identifier)

# can_bridge_ref = ChildRef("can_bridge").with_nodetype(type_can_bridge)
# can_bridge_rule = MakeChild().with_child_reference(can_bridge_ref)
# type_resistor.add(can_bridge_rule, name=can_bridge_ref._identifier)


# # ## CAPACITOR TYPE ###
# type_capacitor = NodeType("Capacitor")
# cp1_ref = ChildRef("p1").with_nodetype(type_electrical)
# cp1_rule = MakeChild().with_child_reference(cp1_ref)
# type_capacitor.add(cp1_rule, name=cp1_ref._identifier)

# cp2_ref = ChildRef("p2").with_nodetype(type_electrical)
# cp2_rule = MakeChild().with_child_reference(cp2_ref)
# type_capacitor.add(cp2_rule, name=cp2_ref._identifier)

# capacitance_ref = ChildRef("capacitance").with_nodetype(type_parameter)
# capacitance_rule = MakeChild().with_child_reference(capacitance_ref)
# type_capacitor.add(capacitance_rule, name=capacitance_ref._identifier)

# max_voltage_ref = ChildRef("max_voltage").with_nodetype(type_parameter)
# max_voltage_rule = MakeChild().with_child_reference(max_voltage_ref)
# type_capacitor.add(max_voltage_rule, name=max_voltage_ref._identifier)

# can_bridge_ref = ChildRef("can_bridge").with_nodetype(type_can_bridge)
# can_bridge_rule = MakeChild().with_child_reference(can_bridge_ref)
# type_capacitor.add(can_bridge_rule, name=can_bridge_ref._identifier)


# ## RC FILTER TYPE ##
# type_rc_filter = NodeType("RCFilter")
# in_ref = ChildRef("in_").with_nodetype(type_electrical)
# in_rule = MakeChild().with_child_reference(in_ref)
# type_rc_filter.add(in_rule, name=in_ref._identifier)

# out_ref = ChildRef("out").with_nodetype(type_electrical)
# out_rule = MakeChild().with_child_reference(out_ref)
# type_rc_filter.add(out_rule, name=out_ref._identifier)

# resistor_ref = ChildRef("resistor").with_nodetype(type_resistor)
# resistor_rule = MakeChild().with_child_reference(resistor_ref)
# type_rc_filter.add(resistor_rule, name=resistor_ref._identifier)

# capacitor_ref = ChildRef("capacitor").with_nodetype(type_capacitor)
# capacitor_rule = MakeChild().with_child_reference(capacitor_ref)
# type_rc_filter.add(capacitor_rule, name=capacitor_ref._identifier)

# cutoff_frequency_ref = ChildRef("cutoff_frequency").with_nodetype(type_parameter)
# cutoff_frequency_rule = MakeChild().with_child_reference(cutoff_frequency_ref)
# type_rc_filter.add(cutoff_frequency_rule, name=cutoff_frequency_ref._identifier)


# r_nref = NestedReference().with_child_reference(resistor_ref)
# rp2_nref = NestedReference().with_child_reference(p2_ref)
# r_nref.next.connect(rp2_nref.prev)

# c_nref = NestedReference().with_child_reference(capacitor_ref)
# cp1_nref = NestedReference().with_child_reference(cp1_ref)
# c_nref.next.connect(cp1_nref.prev)

# rp1_cp1_connection = Connect().with_nested_references([r_nref, c_nref])
# type_rc_filter.add(rp1_cp1_connection, name="rp2_cp1_connection")

# print(dummy_node.children.get_children())

# gifs = resistor.self_gif.get_gif_edges()
# print([gif.name for gif in gifs])

# node_type = NodeType("Resistor")
# children = node_type.children.get_children()
# gifs = node_type.self_gif.get_gif_edges()
# print([gif.name for gif in gifs])
# node_type.instances.connect(resistor.type)


# resistor_instance = type_resistor.execute()
# resistor_instance2 = type_resistor.execute()
# capacitor_instance = type_capacitor.execute()
# rc_filter_instance = type_rc_filter.execute()
# electric_signal_instance = type_electrical.execute()

# NEW EXAMLES --------------------------------------------------------------------------
# print(Type_ImplementsTrait.get_children(direct_only=True, types=[_Node]))

# ### ELECTRICAL TYPE ###
# Type_Electrical = Class_ImplementsType.init_type_node(_Node(), "Electrical")
# # electrical = instantiate(Type_Electrical)

# ### RESISTOR TYPE ###
# Type_Resistor = Class_ImplementsType.init_type_node(_Node(), "Resistor")

# p1_ref = Class_ChildReference.init_child_reference_instance(
#     Type_Electrical, instantiate(Type_Electrical), "p1"
# )
# p1_rule = Class_MakeChild.init_make_child_instance(instantiate(Type_MakeChild), p1_ref)
# Type_Resistor.children.connect(p1_rule.parent, LinkNamedParent("p1"))

# p2_ref = Class_ChildReference.init_child_reference_instance(
#     Type_Electrical, instantiate(Type_Electrical), "p2"
# )
# p2_rule = Class_MakeChild.init_make_child_instance(instantiate(Type_MakeChild), p2_ref)
# Type_Resistor.children.connect(p2_rule.parent, LinkNamedParent("p2"))

# ### CAPACITOR TYPE ###
# Type_Capacitor = Class_ImplementsType.init_type_node(_Node(), "Capacitor")

# c1_ref = Class_ChildReference.init_child_reference_instance(
#     Type_Electrical, instantiate(Type_Electrical), "p1"
# )
# c1_rule = Class_MakeChild.init_make_child_instance(instantiate(Type_MakeChild), c1_ref)
# Type_Capacitor.children.connect(c1_rule.parent, LinkNamedParent("p1"))

# c2_ref = Class_ChildReference.init_child_reference_instance(
#     Type_Electrical, instantiate(Type_Electrical), "p2"
# )
# c2_rule = Class_MakeChild.init_make_child_instance(instantiate(Type_MakeChild), c2_ref)
# Type_Capacitor.children.connect(c2_rule.parent, LinkNamedParent("p2"))

# ### RC FILTER TYPE ###
# Type_RCFilter = Class_ImplementsType.init_type_node(_Node(), "RCFilter")

# r_ref = Class_ChildReference.init_child_reference_instance(
#     Type_Resistor, instantiate(Type_Resistor), "resistor"
# )
# r_rule = Class_MakeChild.init_make_child_instance(instantiate(Type_MakeChild), r_ref)
# Type_RCFilter.children.connect(r_rule.parent, LinkNamedParent("resistor"))

# c_ref = Class_ChildReference.init_child_reference_instance(
#     Type_Capacitor, instantiate(Type_Capacitor), "capacitor"
# )
# c_rule = Class_MakeChild.init_make_child_instance(instantiate(Type_MakeChild), c_ref)
# Type_RCFilter.children.connect(c_rule.parent, LinkNamedParent("capacitor"))

# r1p1_ref = Class_NestedReference.init_nested_reference_instance(
#     instantiate(Type_NestedReference), p1_ref, None
# )
# r1_ref = Class_NestedReference.init_nested_reference_instance(
#     instantiate(Type_NestedReference), r_ref, r1p1_ref
# )

# c1p2_ref = Class_NestedReference.init_nested_reference_instance(
#     instantiate(Type_NestedReference), c2_ref, None
# )
# c2_ref = Class_NestedReference.init_nested_reference_instance(
#     instantiate(Type_NestedReference), c_ref, c1p2_ref
# )

# p1p2_connect_rule = Class_Connect.init_connect_node_instance(
#     instantiate(Type_Connect), [r1_ref, c2_ref]
# )
# Type_RCFilter.children.connect(p1p2_connect_rule.parent, LinkNamedParent("p1p2connect"))


# resistor = instantiate(Type_Resistor)
# capacitor = instantiate(Type_Capacitor)
# rc_filter = instantiate(Type_RCFilter)


# --------------- Visualization ---------------
# !!AI SLOP!! from here on out


def _collect_from(
    start: Node,
    graph=None,
) -> tuple[list[Node], list[tuple[GraphInterface, GraphInterface, object | None]]]:
    """
    Traverse graph from a starting hypernode by following children edges.
    Returns discovered hypernodes and interface-level edges.
    """
    seen_nodes: set[Node] = set()
    nodes: list[Node] = []
    # Store (from_gif, to_gif, link_or_none)
    iface_edges: list[tuple[GraphInterface, GraphInterface, object | None]] = []
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

        # connect self to owned interfaces (layout helper only; no real link)
        for gif in all_gifs:
            key = (id(n.self_gif), id(gif))
            if key not in seen_if_ids:
                seen_if_ids.add(key)
                iface_edges.append((n.self_gif, gif, None))

        # from every owned interface, follow connections (with link type)
        for lg in all_gifs:
            # use edges dict to fetch Link objects
            try:
                edge_map = lg.edges
            except Exception:
                edge_map = {other: None for other in lg.get_gif_edges()}
            for other, link in edge_map.items():
                key = (id(lg), id(other))
                if key not in seen_if_ids:
                    seen_if_ids.add(key)
                    iface_edges.append((lg, other, link))
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
    def __init__(self, root: _Node, figsize: tuple[int, int] = (20, 14)):
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
        for a, b, _link in self.iface_edges:
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
            # Treat Class_ImplementsType.Proto_Type as type nodes
            try:
                from faebryk.core.type import Class_ImplementsType

                return isinstance(n, Class_ImplementsType.Proto_Type)
            except Exception:
                return False

        def _is_rule(n: Node) -> bool:
            # MakeChild nodes in the type graph
            try:
                from faebryk.core.type import Class_MakeChild

                return isinstance(n, Class_MakeChild.Proto_MakeChild)
            except Exception:
                return False

        def _is_instance(n: Node) -> bool:
            # Instance nodes have an is_type hierarchical GIF connected to a type's instances
            if _is_nodetype(n) or _is_rule(n):
                return False
            try:
                is_type_gif = getattr(n, "is_type", None)
                if is_type_gif is None:
                    return False
                parent = is_type_gif.get_parent()
                return parent is not None
            except Exception:
                return False

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

        # Stagger instances vertically so they are not on the same height,
        # but still roughly at the instance level
        base_y_instances = -3 * level_gap_y
        inst_list = levels.get(3, [])
        for i, inst in enumerate(inst_list):
            if inst not in self.hn_pos:
                continue
            x, _y = self.hn_pos[inst]
            sign = -1 if i % 2 else 1
            amplitude = 0.3 * level_gap_y + (i // 2) * 4.0
            self.hn_pos[inst] = (x, base_y_instances + sign * amplitude)

        # Stagger child-instances per parent to emphasize grouping,
        # keep them below the instance level
        base_y_children = -4 * level_gap_y
        for parent, ch in instance_to_children.items():
            for j, child in enumerate(ch):
                if child not in self.hn_pos:
                    continue
                cx, _cy = self.hn_pos[child]
                self.hn_pos[child] = (cx, base_y_children - j * 6.0)

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
                    p for p in self.hn_adj.get(n, set()) if levels.get(p) == l - 1
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
        """Separate overlapping nodes using force-based positioning and real radii."""

        def node_draw_radius(n: Node) -> float:
            # Mirror the interface radius logic used later for drawing
            try:
                k = max(1, len(_interfaces_of(n, self.graph)))
            except Exception:
                k = 1
            r_if_local = max(6.0, 1.2 * k)
            return r_if_local * 1.9  # match drawing scale

        max_iterations = 200
        padding = 8.0
        force_strength = 0.25
        damping = 0.6
        max_step = 6.0

        # Keep root fixed to stabilize layout
        fixed_nodes = {self.root}

        for _ in range(max_iterations):
            forces = {node: (0.0, 0.0) for node in self.hn_pos.keys()}

            # Pairwise repulsion if circles overlap (based on radii)
            nodes_list = list(self.hn_pos.keys())
            for i, n1 in enumerate(nodes_list):
                x1, y1 = self.hn_pos[n1]
                r1 = node_draw_radius(n1)
                for n2 in nodes_list[i + 1 :]:
                    x2, y2 = self.hn_pos[n2]
                    r2 = node_draw_radius(n2)

                    dx = x2 - x1
                    dy = y2 - y1
                    dist = math.hypot(dx, dy)
                    min_dist = r1 + r2 + padding

                    if dist == 0:
                        # Nudge randomly if perfectly overlapping
                        dx, dy, dist = 1.0, 0.0, 1.0

                    if dist < min_dist:
                        overlap = (min_dist - dist) / dist
                        fx = -dx * overlap * force_strength
                        fy = -dy * overlap * force_strength

                        fx = max(-max_step, min(max_step, fx))
                        fy = max(-max_step, min(max_step, fy))

                        if n1 not in fixed_nodes:
                            forces[n1] = (forces[n1][0] + fx, forces[n1][1] + fy)
                        if n2 not in fixed_nodes:
                            forces[n2] = (forces[n2][0] - fx, forces[n2][1] - fy)

            # Apply forces
            total_movement = 0.0
            for n, (fx, fy) in forces.items():
                if n in fixed_nodes:
                    continue
                x, y = self.hn_pos[n]
                dx = fx * damping
                dy = fy * damping
                if dx or dy:
                    self.hn_pos[n] = (x + dx, y + dy)
                    total_movement += abs(dx) + abs(dy)

            if total_movement < 0.05:
                break

    def _node_label(self, n: _Node) -> str:
        return (
            getattr(n, "identifier", None)
            or getattr(n, "_identifier", None)  # show ChildRef identifier
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
                from faebryk.core.type import (
                    Class_ChildReference,
                    Class_ImplementsType,
                    Class_MakeChild,
                )

                is_nodetype = isinstance(n, Class_ImplementsType.Proto_Type)
                is_rule = isinstance(n, Class_MakeChild.Proto_MakeChild)
                is_childref = isinstance(n, Class_ChildReference.Proto_ChildReference)
            except Exception:
                is_nodetype = False
                is_rule = False
                is_childref = False

            # Fallback to structural checks (attributes) if Protocol isinstance fails
            if not is_rule and hasattr(n, "child_ref_pointer"):
                is_rule = True
            if not is_childref and hasattr(n, "node_type_pointer"):
                is_childref = True

            # Additional fallback: if node has is_type parent whose identifier/name is "MakeChild"
            if not is_rule:
                try:
                    is_type_gif = getattr(n, "is_type", None)
                    if is_type_gif is not None:
                        parent_info = is_type_gif.get_parent()
                        if parent_info is not None:
                            pnode, _pname = parent_info
                            pid = (
                                getattr(pnode, "_identifier", None)
                                or getattr(pnode, "identifier", None)
                                or pnode.get_name()
                            )
                            if pid == "MakeChild":
                                is_rule = True
                except Exception:
                    pass

            if is_nodetype:
                ec_color = "#000000"
                face_color = "#e8f0fe"
            elif is_rule or is_childref:
                ec_color = "#d33"
                face_color = "#ffe8e8"
            else:
                # Instances/others → green
                ec_color = "#2ca02c"
                face_color = "#e8fbe8"

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

            # Label offsets scaled with circle radius
            label_offset = max(0.5, 0.55 * r_draw)

            # main name centered inside the circle
            main_text = self.ax.text(
                cx,
                cy,
                label_main,
                ha="center",
                va="center",
                fontsize=12,
                weight="bold",
                zorder=20,
            )
            # type below center
            type_text = self.ax.text(
                cx,
                cy - label_offset,
                f"[{label_type}]",
                ha="center",
                va="center",
                fontsize=7,
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
        for a, b, link in self.iface_edges:
            pa = self.pos.get(a)
            pb = self.pos.get(b)
            if pa is None or pb is None:
                continue

            edge_color = "#7a7a7a"
            edge_width = 1.3
            edge_alpha = 0.7

            try:
                # Highest priority: link type
                from faebryk.core.link import LinkPointer as _LP

                if link is not None and isinstance(link, _LP):
                    edge_color = "#ff7f0e"  # orange for LinkPointer
                    edge_width = 1.7
                elif a.name == "rules" or b.name == "rules":
                    edge_color = "#d33"  # rule connections
                    edge_width = 1.5
                elif (
                    a.name == "is_type"
                    or b.name == "is_type"
                    or a.name == "instances"
                    or b.name == "instances"
                ):
                    edge_color = "#2ca02c"  # type-instance connections
                    edge_width = 1.5
                elif a.name == "connections" or b.name == "connections":
                    edge_color = "#1f77b4"  # connections interfaces -> blue
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


def visualize_type_graph(root: _Node, figsize: tuple[int, int] = (20, 14)) -> None:
    """Create and display an interactive type graph visualization"""
    visualizer = InteractiveTypeGraphVisualizer(root, figsize)
    visualizer.show()


# Ensure registry runs for these Python classes and autogen rules are created

# register_python_nodetype(PyResistor)
# register_python_nodetype(PyCapacitor)

r = F.Resistor()

visualize_type_graph(Type_ImplementsType)
