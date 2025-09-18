import faebryk.library._F as F
from faebryk.core.graphinterface import GraphInterface, GraphInterfaceReference
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.core.parameter import Parameter
from faebryk.libs.library import L
from faebryk.libs.units import P

# class Attribute[T = str | int | float]:
#     def __init__(self, value: T | None) -> None:
#         self.name: str | None = None
#         self.value = value


class NodeType(Node):
    def __init__(self, identifier: str):
        super().__init__()
        self.identifier = identifier

    rules: GraphInterface
    instances: GraphInterface
    type: GraphInterface

    def __postinit__(self):
        pass
        # self.add(GraphInterface(), "rules")

    def execute(self) -> Node:
        node = Node()
        for rule in self.rules.get_connected_nodes([Rule]):
            assert isinstance(rule, Rule)
            rule.execute(node)

        return node


class Rule(Node):
    def execute(self, node: Node) -> None:
        pass


class FieldDeclaration(Rule):
    def __init__(self, name: str | None, type: type[Node]):
        super().__init__()
        self.name = name
        self.nodetype = type

    def execute(self, node: Node) -> None:
        super().execute(node)
        obj = self.nodetype()

        node.add(obj, name=self.name)


class MakeChild(Rule):
    def __init__(self, name: str | None, nodetype: NodeType):
        super().__init__()
        self.name = name
        self.nodetype = nodetype

    def execute(self, node: Node) -> None:
        super().execute(node)
        obj = self.nodetype.execute()

        node.add(obj, name=self.name)


class Connect(Rule):
    pass


##### MAKING TYPEGRAPH #####
type_sentinel = NodeType("Type")
type_make_child = NodeType("MakeChild")
type_trait = NodeType("Trait")

## CAN BRIDGE TYPE ##
type_can_bridge = NodeType("CanBridge")
type_can_bridge.rules.connect(MakeChild(name="trait", nodetype=type_trait).self_gif)
# TODO: add in and out for this trait so it can be connected to other interfaces
# type_can_bridge.rules.connect(MakeChild)

## ELECTRICAL TYPE ##
type_electrical = NodeType("Electrical")

### RESISTOR TYPE ###
type_resistor = NodeType("Resistor")
type_resistor.rules.connect(MakeChild("p1", type_electrical).self_gif)
type_resistor.rules.connect(MakeChild("p2", type_electrical).self_gif)
type_resistor.rules.connect(FieldDeclaration("resistance", Parameter).self_gif)
type_resistor.rules.connect(FieldDeclaration("max_power", Parameter).self_gif)
type_resistor.rules.connect(FieldDeclaration("max_voltage", Parameter).self_gif)
type_resistor.rules.connect(MakeChild(name="can_brdidge", nodetype=type_trait).self_gif)

### CAPACITOR TYPE ###
type_capacitor = NodeType("Capacitor")
type_capacitor.rules.connect(MakeChild("p1", type_electrical).self_gif)
type_capacitor.rules.connect(MakeChild("p2", type_electrical).self_gif)
type_capacitor.rules.connect(FieldDeclaration("capacitance", Parameter).self_gif)
type_capacitor.rules.connect(FieldDeclaration("max_voltage", Parameter).self_gif)
type_capacitor.rules.connect(
    MakeChild(name="can_brdidge", nodetype=type_trait).self_gif
)

## RC FILTER TYPE ##
type_rc_filter = NodeType("RCFilter")
type_rc_filter.rules.connect(MakeChild("in_", type_electrical).self_gif)
type_rc_filter.rules.connect(MakeChild("out", type_electrical).self_gif)
type_rc_filter.rules.connect(MakeChild("resistor", type_resistor).self_gif)
type_rc_filter.rules.connect(MakeChild("capacitor", type_capacitor).self_gif)

## DUMMY NODE ##

type_dummy_node = NodeType("Dummy")
dummy_rule = FieldDeclaration("Dummy Field", Parameter)
type_dummy_node.rules.connect(dummy_rule.self_gif)

# type_resistor.rules.connect

dummy_node = type_dummy_node.execute()

print(dummy_node.children.get_children())

# gifs = resistor.self_gif.get_gif_edges()
# print([gif.name for gif in gifs])

# node_type = NodeType("Resistor")
# children = node_type.children.get_children()
# gifs = node_type.self_gif.get_gif_edges()
# print([gif.name for gif in gifs])
# node_type.instances.connect(resistor.type)

# --------------- Visualization ---------------
import math
import matplotlib.pyplot as plt
import networkx as nx
from collections import deque


def _collect_from(
    start: Node,
) -> tuple[list[Node], list[tuple[GraphInterface, GraphInterface]]]:
    """
    Traverse graph from a starting hypernode by following children edges.
    Returns discovered hypernodes and interface-level edges.
    """
    seen_nodes: set[Node] = set()
    nodes: list[Node] = []
    iface_edges: list[tuple[GraphInterface, GraphInterface]] = []

    q: deque[Node] = deque([start])
    while q:
        n = q.popleft()
        if n in seen_nodes:
            continue
        seen_nodes.add(n)
        nodes.append(n)

        # enqueue children (hypernodes)
        for child in n.children.get_children():
            q.append(child)

        # collect edges from self gif to others to discover interfaces
        for gif in n.self_gif.get_gif_edges():
            # record interface edges (both directions implied by graph)
            iface_edges.append((n.self_gif, gif))

    return nodes, iface_edges


def _interfaces_of(node: Node) -> list[GraphInterface]:
    # All GIFs connected to self are considered node-local interfaces
    gifs = list(node.self_gif.get_gif_edges())
    # ensure self also included as the root interface for the hypernode
    if node.self_gif not in gifs:
        gifs.append(node.self_gif)
    return gifs


def visualize_type_graph(root: Node, figsize: tuple[int, int] = (12, 8)) -> None:
    nodes, iface_edges = _collect_from(root)

    # Build a NetworkX graph at the interface level
    G = nx.Graph()

    # Map each interface to its owning hypernode
    iface_to_node: dict[GraphInterface, Node] = {}
    for n in nodes:
        for gif in _interfaces_of(n):
            G.add_node(gif)
            iface_to_node[gif] = n

    for a, b in iface_edges:
        if a in G and b in G:
            G.add_edge(a, b)

    # Layout: place hypernodes in a circle, interfaces inside each
    num_hn = max(1, len(nodes))
    R = 5.0
    hn_pos: dict[Node, tuple[float, float]] = {}
    for i, n in enumerate(nodes):
        angle = 2 * math.pi * i / num_hn
        hn_pos[n] = (R * math.cos(angle), R * math.sin(angle))

    # Place interfaces within each hypernode in a smaller circle
    pos: dict[GraphInterface, tuple[float, float]] = {}
    r_if = 1.2
    for n in nodes:
        center = hn_pos[n]
        ifaces = _interfaces_of(n)
        k = max(1, len(ifaces))
        for j, gif in enumerate(ifaces):
            a = 2 * math.pi * j / k
            pos[gif] = (center[0] + r_if * math.cos(a), center[1] + r_if * math.sin(a))

    # Draw
    fig, ax = plt.subplots(figsize=figsize)

    # Draw hypernodes as big circles
    for n in nodes:
        cx, cy = hn_pos[n]
        circle = plt.Circle(
            (cx, cy), r_if * 1.4, color="#e8f0fe", ec="#6c8cd5", lw=1.5, alpha=0.7
        )
        ax.add_patch(circle)
        ax.text(
            cx,
            cy,
            n.get_name(True) or n.__class__.__name__,
            ha="center",
            va="center",
            fontsize=10,
        )

    # Draw interface edges
    nx.draw_networkx_edges(G, pos=pos, ax=ax, edge_color="#7a7a7a", alpha=0.6)

    # Draw interfaces as small nodes
    nx.draw_networkx_nodes(
        G, pos=pos, ax=ax, node_size=200, node_color="#ffe8cc", edgecolors="#cc7a00"
    )

    # Label interfaces with their names
    labels = {gif: gif.name for gif in G.nodes}
    nx.draw_networkx_labels(G, pos=pos, labels=labels, font_size=8)

    ax.set_aspect("equal")
    ax.axis("off")
    plt.tight_layout()
    plt.show()


# Start visualization from type_sentinel
visualize_type_graph(type_sentinel)
