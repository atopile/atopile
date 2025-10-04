"""Lightweight Python mock of the Zig-backed graph API.

This can be used while the Zig implementation is still in flux.  The goal is
API compatibility, not feature parity, so only the pieces exercised by the
current Python code are implemented.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Generator
from typing import TypedDict, TypeVar

from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.node_type import EdgeType
from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, Edge, Node
from faebryk.libs.util import Tree, cast_assert

Literal = int | float | str | bool
_ContextT = TypeVar("_ContextT")


# TODO: @python3.15 (PEP 728) extra_items=Literal
class LiteralArgs(TypedDict): ...


class NodeHelpers:
    @staticmethod
    def get_neighbours(
        bound_node: BoundNode, edge_type: Edge.Type
    ) -> Generator[BoundNode, None, None]:
        neighbours: list[BoundNode] = []

        def collect(acc: list[BoundNode], bound_edge: BoundEdge) -> None:
            edge = bound_edge.edge()
            if edge.source().is_same(other=bound_node.node()):
                acc.append(bound_node.g().bind(node=edge.target()))
            elif edge.target().is_same(other=bound_node.node()):
                acc.append(bound_node.g().bind(node=edge.source()))

        bound_node.visit_edges_of_type(edge_type=edge_type, ctx=neighbours, f=collect)
        yield from neighbours

    @staticmethod
    def get_type_name(bound_node: BoundNode) -> str:
        types = []

        def collect(acc: list[str], bound_edge: BoundEdge) -> None:
            edge = bound_edge.edge()
            if name := edge.target().get_attr(key="name"):
                acc.append(cast_assert(str, name))

        bound_node.visit_edges_of_type(
            edge_type=EdgeType.get_tid(), ctx=types, f=collect
        )

        assert len(types) == 1
        (t,) = types
        return t

    @staticmethod
    def print_tree(
        bound_node: BoundNode, renderer: Callable[[BoundNode], str] = repr
    ) -> None:
        edge_type = EdgeComposition.get_tid()

        def iter_children(node: BoundNode) -> list[BoundNode]:
            children: list[BoundNode] = []
            graph_view = node.g()
            source_node = node.node()

            def add_child(acc: list[BoundNode], bound_edge: BoundEdge) -> None:
                edge = bound_edge.edge()
                if edge.source().is_same(other=source_node):
                    acc.append(graph_view.bind(node=edge.target()))

            node.visit_edges_of_type(edge_type=edge_type, ctx=children, f=add_child)
            return children

        def build_tree(node: BoundNode, ancestors: list[Node]) -> Tree[BoundNode]:
            current_node = node.node()
            if any(ancestor.is_same(other=current_node) for ancestor in ancestors):
                return Tree()
            next_ancestors = [*ancestors, current_node]
            children = iter_children(node)
            return Tree(
                OrderedDict(
                    (child, build_tree(child, next_ancestors)) for child in children
                )
            )

        root = bound_node
        tree = Tree(OrderedDict([(root, build_tree(root, []))]))

        pretty = tree.pretty_print(node_renderer=renderer)
        if pretty:
            print(pretty, end="")
