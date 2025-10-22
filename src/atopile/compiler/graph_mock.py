"""Lightweight Python mock of the Zig-backed graph API.

This can be used while the Zig implementation is still in flux.  The goal is
API compatibility, not feature parity, so only the pieces exercised by the
current Python code are implemented.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Generator, Sequence
from typing import TypedDict, TypeVar

import faebryk.core.node as fabll
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
    def get_children(bound_node: BoundNode) -> dict[str, BoundNode]:
        children: dict[str, BoundNode] = {}

        def collect(acc: dict[str, BoundNode], bound_edge: BoundEdge) -> None:
            edge = bound_edge.edge()
            if edge.source().is_same(other=bound_node.node()):
                # TODO: handle unnamed children
                acc[EdgeComposition.get_name(edge=edge)] = bound_edge.g().bind(
                    node=edge.target()
                )

        bound_node.visit_edges_of_type(
            edge_type=EdgeComposition.get_tid(), ctx=children, f=collect
        )

        return children

    @staticmethod
    def get_child(bound_node: BoundNode, identifier: str) -> BoundNode | None:
        return NodeHelpers.get_children(bound_node).get(identifier)

    @staticmethod
    def get_type_name(n: BoundNode) -> str | None:
        # if (type_edge := EdgeType.get_type_edge(bound_node=n)) is None:
        return None

        # type_node = EdgeType.get_type_node(edge=type_edge.edge())
        # type_bound = type_edge.g().bind(node=type_node)
        # type_name = type_bound.node().get_attr(key="type_identifier")
        return "type_name"
        # return cast_assert(str, type_name)

    @staticmethod
    def print_tree(
        bound_node: BoundNode,
        renderer: Callable[[BoundEdge | None, BoundNode], str] | None = None,
        edge_types: Sequence[type] | None = None,
        exclude_node_types: Sequence[str] | None = None,
    ) -> None:
        edge_type_classes: Sequence[type] = edge_types or (EdgeComposition,)
        edge_type_ids: list[int] = []
        for edge_type_cls in edge_type_classes:
            get_tid = getattr(edge_type_cls, "get_tid", None)
            if not callable(get_tid):
                raise AttributeError(
                    f"{edge_type_cls!r} must expose a callable get_tid() returning an edge type id"
                )
            edge_type_ids.append(cast_assert(int, get_tid()))

        exclude_types = frozenset(exclude_node_types or ())

        if exclude_types:
            root_type = NodeHelpers.get_type_name(bound_node)
            if root_type is not None and root_type in exclude_types:
                return

        if renderer is None:

            def default_renderer(edge: BoundEdge | None, node: BoundNode) -> str:
                if edge is None:
                    return repr(node)
                edge_obj = edge.edge()
                label = edge_obj.name() or repr(edge_obj)
                return f"{label} -> {node!r}"

            renderer = default_renderer

        def iter_children(node: BoundNode) -> list[tuple[BoundEdge, BoundNode]]:
            children: list[tuple[BoundEdge, BoundNode]] = []
            graph_view = node.g()
            source_node = node.node()

            def add_child(
                acc: list[tuple[BoundEdge, BoundNode]], bound_edge: BoundEdge
            ) -> None:
                edge = bound_edge.edge()
                if edge.source().is_same(other=source_node):
                    child_node = graph_view.bind(node=edge.target())
                    if exclude_types:
                        child_type = NodeHelpers.get_type_name(child_node)
                        if child_type is not None and child_type in exclude_types:
                            return
                    acc.append((bound_edge, child_node))

            for edge_type_id in edge_type_ids:
                node.visit_edges_of_type(
                    edge_type=edge_type_id, ctx=children, f=add_child
                )
            return children

        edge_lookup: dict[BoundNode, BoundEdge | None] = {bound_node: None}

        def build_tree(node: BoundNode, ancestors: list[Node]) -> Tree[BoundNode]:
            current_node = node.node()
            if any(ancestor.is_same(other=current_node) for ancestor in ancestors):
                return Tree()
            next_ancestors = [*ancestors, current_node]
            children = iter_children(node)
            items: list[tuple[BoundNode, Tree[BoundNode]]] = []
            for edge, child in children:
                edge_lookup.setdefault(child, edge)
                items.append((child, build_tree(child, next_ancestors)))
            return Tree(OrderedDict(items))

        root = bound_node
        tree = Tree(OrderedDict([(root, build_tree(root, []))]))

        assert renderer is not None

        def render_node(node: BoundNode) -> str:
            inbound_edge = edge_lookup.get(node)
            return renderer(inbound_edge, node)

        pretty = tree.pretty_print(node_renderer=render_node)
        if pretty:
            print(pretty, end="")
