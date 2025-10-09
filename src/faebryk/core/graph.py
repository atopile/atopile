# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import io
import logging
from types import UnionType
from typing import TYPE_CHECKING, Any, overload

from faebryk.core.cpp import Graph
from faebryk.core.node import Node
from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.node_type import EdgeType
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundNode

if TYPE_CHECKING:
    from faebryk.core.trait import Trait

logger = logging.getLogger(__name__)


# TODO move these to C++
# just here for making refactoring easier for the moment
# a bit weird typecheck
class GraphFunctions:
    # Make all kinds of graph filtering functions so we can optimize them in the future
    # Avoid letting user query all graph nodes always because quickly very slow
    def __init__(self, *graph: Graph):
        self.graph = graph

    def node_projection(self) -> list["Node"]:
        return list(self.nodes_of_type(Node))

    def nodes_with_trait[T: "Trait"](self, trait: type[T]) -> list[tuple["Node", T]]:
        return [
            (n, n.get_trait(trait))
            for n in self.node_projection()
            if n.has_trait(trait)
        ]

    # TODO: Waiting for python to add support for type mapping
    def nodes_with_traits[*Ts](
        self, traits: tuple[*Ts]
    ):  # -> list[tuple[Node, tuple[*Ts]]]:
        return [
            (n, tuple(n.get_trait(trait) for trait in traits))  # type: ignore
            for n in self.node_projection()
            if all(n.has_trait(trait) for trait in traits)  # type: ignore
        ]

    def nodes_of_type[T: "Node"](self, t: type[T]) -> set[T]:
        return {n for g in self.graph for n in g.node_projection() if isinstance(n, t)}

    @overload
    def nodes_of_types(self, t: tuple[type["Node"], ...]) -> set["Node"]: ...
    @overload
    def nodes_of_types(self, t: UnionType) -> set["Node"]: ...

    def nodes_of_types(self, t):  # type: ignore TODO
        return {n for g in self.graph for n in g.node_projection() if isinstance(n, t)}


class TypeGraphFunctions:
    @staticmethod
    def create(root: "Node") -> tuple["TypeGraph", "BoundNode"]:
        from faebryk.core.trait import Trait

        typegraph = TypeGraph.create()
        type_nodes: dict[type[Node], BoundNode] = {}
        make_child_nodes: dict[tuple[type[Node], str], BoundNode] = {}

        def ensure_type_node(cls: type[Node]) -> BoundNode:
            if cls in type_nodes:
                return type_nodes[cls]

            type_node = typegraph.init_type_node(identifier=cls._type_identifier())
            type_nodes[cls] = type_node

            if issubclass(cls, Trait):
                trait_marker = typegraph.init_trait_node()
                EdgeComposition.add_child(
                    bound_node=type_node,
                    child=trait_marker.node(),
                    child_identifier="implements_trait",
                )

            return type_node

        def ensure_make_child(
            parent_cls: type[Node], identifier: str, child_cls: type[Node]
        ) -> None:
            if (key := (parent_cls, identifier)) in make_child_nodes:
                return

            parent_type = ensure_type_node(parent_cls)
            child_type = ensure_type_node(child_cls)
            make_child = typegraph.init_make_child_node(
                type_node=child_type,
                identifier=identifier,
            )
            EdgeComposition.add_child(
                bound_node=parent_type,
                child=make_child.node(),
                child_identifier=identifier,
            )

            make_child_nodes[key] = make_child

        def walk(node: Node) -> None:
            ensure_type_node(type(node))
            for name, child in node._iter_direct_children():
                ensure_make_child(type(node), name, type(child))
                walk(child)

        walk(root)
        root_bound = ensure_type_node(type(root))
        return typegraph, root_bound

    @staticmethod
    def render(root: BoundNode) -> str:
        stream = io.StringIO()

        def bind_target(bound_edge) -> BoundNode:
            target_node = bound_edge.edge().target()
            return bound_edge.g().bind(node=target_node)

        def resolve_child_type(make_child_bound: BoundNode) -> BoundNode | None:
            children_edges: list[Any] = []

            def collect(ctx, edge):
                ctx.append(edge)

            EdgeComposition.visit_children_edges(
                bound_node=make_child_bound, ctx=children_edges, f=collect
            )

            if not children_edges:
                return None

            for ref_edge in children_edges:
                reference_bound = bind_target(ref_edge)
                pointer_edges: list[Any] = []

                def collect_pointer(ctx, edge):
                    ctx.append(edge)

                reference_bound.visit_edges_of_type(
                    edge_type=EdgePointer.get_tid(),
                    ctx=pointer_edges,
                    f=collect_pointer,
                )

                for pointer_edge in pointer_edges:
                    return bind_target(pointer_edge)

            return None

        def get_node_label(bound_node: BoundNode) -> str:
            try:
                type_edge = EdgeType.get_type_edge(bound_node=bound_node)
            except Exception:
                type_edge = None

            if type_edge is not None:
                type_node = EdgeType.get_type_node(edge=type_edge.edge())
                type_bound = type_edge.g().bind(node=type_node)
                type_name = type_bound.node().get_attr(key="name")

                if isinstance(type_name, str):
                    return type_name

            if isinstance(attr := bound_node.node().get_attr(key="name"), str):
                return attr

            if isinstance(uuid := bound_node.node().get_attr(key="uuid"), int):
                return f"node@{uuid}"

            return repr(bound_node.node())

        def render(bound_node: BoundNode, prefix: str) -> None:
            child_edges: list[Any] = []

            def collect(ctx, edge):
                ctx.append(edge)

            EdgeComposition.visit_children_edges(
                bound_node=bound_node, ctx=child_edges, f=collect
            )

            filtered_edges = [
                (EdgeComposition.get_name(edge=edge.edge()), edge)
                for edge in child_edges
                if not EdgeComposition.get_name(edge=edge.edge()).startswith(
                    "implements_"
                )
            ]
            filtered_edges.sort(key=lambda item: item[0])

            count = len(filtered_edges)
            for idx, (edge_name, bound_edge) in enumerate(filtered_edges):
                is_last = idx == count - 1
                connector = "└──" if is_last else "├──"
                make_child_bound = bind_target(bound_edge)
                child_bound = resolve_child_type(make_child_bound)
                child_label = (
                    get_node_label(child_bound)
                    if child_bound is not None
                    else get_node_label(make_child_bound)
                )
                print(
                    f"{prefix}{connector} [EdgeComposition:{edge_name}] {child_label}",
                    file=stream,
                )
                next_bound = (
                    child_bound if child_bound is not None else make_child_bound
                )
                child_prefix = prefix + ("    " if is_last else "│   ")
                render(next_bound, child_prefix)

        print(get_node_label(root), file=stream)
        render(root, "")

        return stream.getvalue()


class InstanceGraphFunctions:
    @staticmethod
    def create(typegraph: TypeGraph, root: BoundNode) -> "BoundNode":
        return typegraph.instantiate(
            build_target_type_identifier=root.node().get_attr(key="name")
        )

    @staticmethod
    def render(root: BoundNode) -> str:
        stream = io.StringIO()
        visited: set[int] = set()
        labels: dict[int, str] = {}
        counter = [0]

        def node_key(bound_node: BoundNode) -> int:
            return id(bound_node.node())

        def get_node_label(bound_node: BoundNode) -> str:
            if (key := node_key(bound_node)) in labels:
                return labels[key]

            if isinstance(attr := bound_node.node().get_attr(key="name"), str):
                label = attr
            else:
                counter[0] += 1
                label = f"node#{counter[0]}"

            labels[key] = label
            return label

        def collect_children(bound_node: BoundNode) -> list:
            edges: list[Any] = []

            def collect(ctx, edge):
                ctx.append(edge)

            EdgeComposition.visit_children_edges(
                bound_node=bound_node, ctx=edges, f=collect
            )

            return edges

        def render(bound_node: BoundNode, prefix: str) -> None:
            if (key := node_key(bound_node)) in visited:
                print(f"{prefix}(cycle)", file=stream)
                return

            visited.add(key)
            children = []
            for edge in collect_children(bound_node):
                if (name := EdgeComposition.get_name(edge=edge.edge())).startswith(
                    "implements_"
                ):
                    continue
                children.append((name, edge))

            children.sort(key=lambda item: item[0])

            total = len(children)
            for idx, (edge_name, bound_edge) in enumerate(children):
                is_last = idx == total - 1
                connector = "└──" if is_last else "├──"
                child_bound = bound_edge.g().bind(node=bound_edge.edge().target())
                print(
                    f"{prefix}{connector} [EdgeComposition:{edge_name}] {get_node_label(child_bound)}",
                    file=stream,
                )
                child_prefix = prefix + ("    " if is_last else "│   ")
                render(child_bound, child_prefix)

        print(get_node_label(root), file=stream)
        render(root, "")

        return stream.getvalue()
