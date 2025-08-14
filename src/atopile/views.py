from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal
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

class Powertree:
    def __init__(self, graph_fxns: GraphFunctions) -> None:
        self._graph_fxns = graph_fxns

    def _compute_tree(self) -> Tree[_PowerTreeNode]:
        """Compute the power tree structure from the graph.

        This function traverses the graph to identify power sources and their
        relationships. It builds a tree structure where each node represents a bus and
        contains information about the power sources feeding into it.
        """
        tree = Tree[_PowerTreeNode]()

        power_nodes: set[F.Power] = self._graph_fxns.nodes_of_type(F.Power)
        sources = set(n for n in power_nodes if n.has_trait(F.Power.is_power_source))
        root_sources = set(n for n in sources if not n.has_trait(F.Power.is_power_sink))

        # We do not support multiple root sources, so we will throw an error.
        if len(root_sources) > 1:
            raise UserNotImplementedError("Multiple root sources are not supported.")

        buses = ModuleInterface.group_into_buses(power_nodes)
        #breakpoint()

        source_node = next(iter(sources))
        root_source = _PowerTreeNode(source_node.get_full_name(),
                                     source_node.voltage)
        tree[root_source] = Tree[_PowerTreeNode]()

        def walk_graph(into_tree: Tree[_PowerTreeNode], source_node) -> None:
            # Let's walk through the power nodes and find out which ones are sources
            # and which ones are sinks.
            for connected_node in source_node.get_connected():
                node_hierarchy = connected_node.get_hierarchy()

                # TODO(markovejnovic): This feels like a hack, is there a bettery way
                # to do this?
                if node_hierarchy[-1][1] == "reference":
                    continue

                name = connected_node.get_full_name()
                pt_node = _PowerTreeNode(name=name)
                tree[root_source][pt_node] = Tree[_PowerTreeNode]()

                if connected_node.has_trait(F.Power.is_power_source):
                    # The connected node is also a power source so we need to DFS into
                    # it.
                    walk_graph(tree[root_source][pt_node], connected_node)

        walk_graph(tree[root_source], source_node)
        return tree

    def render(self, renderer: Callable[[Tree[_PowerTreeNode]], None]) -> None:
        renderer(self._compute_tree())
