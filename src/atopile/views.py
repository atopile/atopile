from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal
from faebryk.core.graph import GraphFunctions
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.parameter import Parameter
import faebryk.library._F as F
from faebryk.libs.util import Tree
from atopile.errors import UserNotImplementedError

@dataclass(frozen=True)
class _PowerTreeNode:
    name: str
    voltage: Parameter | None = None


def render_cli(tree: Tree[_PowerTreeNode]) -> None:
    def inner(tree: Tree[_PowerTreeNode], depth: int = 0) -> None:
        # Terminal state, there are no more children
        if len(tree.values()) == 0:
            return

        for node, children in tree.items():
            pfx = "└─" if node == list(tree.keys())[-1] else "├─"
            if node.voltage is None:
                print(" " * depth + f"{pfx} {node.name}")
            else:
                print(" " * depth + f"{pfx} {node.name} @ {node.voltage.compact_repr()}")

            inner(children, depth + 1)

    return inner(tree)


def render_dot(tree: Tree[_PowerTreeNode]) -> None:
    """Render the power tree as a DOT graph."""
    lines = ["digraph PowerTree {"]
    lines.append('  node [shape=box];')

    nodes = set()
    edges = []

    def inner(tree: Tree[_PowerTreeNode], parent_name: str | None = None) -> None:
        for node, children in tree.items():
            node_id = f'"{node.name}"'
            nodes.add((node_id, node))

            if parent_name:
                edges.append((parent_name, node_id))

            inner(children, node_id)

    inner(tree)

    # Define all nodes with their attributes
    for node_id, node in nodes:
        if node.voltage is not None:
            lines.append(f'  {node_id} [label="{node.name} @ {node.voltage.compact_repr()}"];')
        else:
            lines.append(f'  {node_id};')

    # Define all edges
    for parent, child in edges:
        lines.append(f'  {parent} -> {child};')

    lines.append("}")
    print("\n".join(lines))

class Powertree:
    def __init__(self, graph_fxns: GraphFunctions) -> None:
        self._graph_fxns = graph_fxns

    def _compute_tree(self, depth: int = 1) -> Tree[_PowerTreeNode]:
        """Compute the power tree structure from the graph.

        This function traverses the graph to identify power sources and their
        relationships. It builds a tree structure where each node represents a bus and
        contains information about the power sources feeding into it.

        Args:
        ----
            depth (int): The maximum depth of hierarchies in the tree to consider.
        """
        def compute_name(node_hierarchy: list[tuple[Any, str]]) -> str:
            """Compute the name of the node based on its hierarchy."""
            return ".".join(str(v[1]) for v in node_hierarchy[1:(1 + depth)])

        tree = Tree[_PowerTreeNode]()

        power_nodes: set[F.Power] = self._graph_fxns.nodes_of_type(F.Power)
        sources = set(n for n in power_nodes if n.has_trait(F.Power.is_power_source))
        root_sources = set(n for n in sources if not n.has_trait(F.Power.is_power_sink))

        # We do not support multiple root sources, so we will throw an error.
        if len(root_sources) > 1:
            raise UserNotImplementedError("Multiple root sources are not supported.")

        source_node = next(iter(sources))
        root_source = _PowerTreeNode(compute_name(source_node.get_hierarchy()),
                                     source_node.voltage)

        tree[root_source] = Tree[_PowerTreeNode]()
        def walk_graph(into_tree: Tree[_PowerTreeNode], source_node) -> None:
            # Let's walk through the power nodes and find out which ones are sources
            # and which ones are sinks.
            for connected_node in source_node.get_connected():
                node_hierarchy = connected_node.get_hierarchy()

                # TODO(markovejnovic): This feels like a hack, is there a better way
                # to do this?
                if node_hierarchy[-1][1] == "reference":
                    continue

                # Another thing worth skipping is when you find a top-level
                # ElectricPower node that is not a source nor a sink -- it's just a tie
                # and adds visual clutter.
                def should_skip_top_level() -> bool:
                    # A node is never truly top-level since the top-level node is
                    # actually the project (I think). Consequently, a node belongs to
                    # the top-level if it only has one parent. The hierarchy includes
                    # the current node.
                    is_top_level = len(node_hierarchy) == 2

                    is_not_source = \
                        not connected_node.has_trait(F.Power.is_power_source)
                    is_not_sink = \
                        not connected_node.has_trait(F.Power.is_power_sink)
                    return is_top_level and is_not_source and is_not_sink

                if should_skip_top_level():
                    continue

                pt_node = _PowerTreeNode(name=compute_name(node_hierarchy))

                # TODO(markovejnovic): This could be faster if we used some sort of
                # hash-set to keep track of already inserted nodes.
                # Before we insert the node into the tree, we need to check if it is
                # already in the tree.
                if tree.contains(pt_node, lambda x: x.name):
                    continue

                into_tree[pt_node] = Tree[_PowerTreeNode]()

                if connected_node.has_trait(F.Power.is_power_source):
                    # The connected node is also a power source so we need to DFS into
                    # it.
                    walk_graph(into_tree[pt_node], connected_node)

        walk_graph(tree[root_source], source_node)
        return tree

    def render(self, renderer: Callable[[Tree[_PowerTreeNode]], None]) -> None:
        renderer(self._compute_tree())
