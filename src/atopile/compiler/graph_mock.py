"""Lightweight Python mock of the Zig-backed graph API.

This can be used while the Zig implementation is still in flux.  The goal is
API compatibility, not feature parity, so only the pieces exercised by the
current Python code are implemented.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Sequence

import faebryk.core.node as fabll
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.graph.graph import BoundEdge, BoundNode, Node
from faebryk.libs.util import Tree, cast_assert


class NodeHelpers:
    @staticmethod
    def print_tree(
        bound_node: BoundNode,
        renderer: Callable[[BoundEdge | None, BoundNode], str] | None = None,
        edge_types: Sequence[type] = (EdgeComposition,),
        exclude_node_types: Sequence[type] | None = None,
    ) -> None:
        edge_type_ids: list[int] = []
        for edge_type_cls in edge_types:
            get_tid = getattr(edge_type_cls, "get_tid", None)
            if not callable(get_tid):
                raise AttributeError(
                    f"{edge_type_cls!r} must expose a callable get_tid()"
                )
            edge_type_ids.append(cast_assert(int, get_tid()))

        exclude_types = frozenset([t.__qualname__ for t in exclude_node_types or ()])

        if exclude_types:
            root_type = fabll.Node.bind_instance(bound_node).get_type_name()
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
                        child_type = fabll.Node.bind_instance(
                            child_node
                        ).get_type_name()
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
