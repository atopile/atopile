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
            # Build label from attributes
            parts = []

            try:
                type_edge = EdgeType.get_type_edge(bound_node=bound_node)
            except Exception:
                type_edge = None

            # Get the type this node is an instance of
            instance_type_name = None
            if type_edge is not None:
                type_node = EdgeType.get_type_node(edge=type_edge.edge())
                type_bound = type_edge.g().bind(node=type_node)
                type_name = type_bound.node().get_attr(key="type_identifier")

                if isinstance(type_name, str):
                    instance_type_name = type_name
                    # For ImplementsType nodes, show what they implement
                    if type_name == "ImplementsType":
                        # Get parent to find the type being implemented
                        parent_edge = EdgeComposition.get_parent_edge(
                            bound_node=bound_node
                        )
                        if parent_edge:
                            parent_node = parent_edge.edge().source()
                            parent_bound = parent_edge.g().bind(node=parent_node)
                            if isinstance(
                                parent_type := parent_bound.node().get_attr(
                                    key="type_identifier"
                                ),
                                str,
                            ):
                                parts.append(f"ImplementsType → {parent_type}")
                            else:
                                parts.append("ImplementsType")
                    else:
                        parts.append(f"type={type_name}")

            # Get type_identifier attribute (for type nodes themselves)
            if isinstance(
                attr := bound_node.node().get_attr(key="type_identifier"), str
            ):
                if not parts or instance_type_name != "ImplementsType":
                    parts.insert(0, attr)

            # Get name attribute (fallback)
            if isinstance(attr := bound_node.node().get_attr(key="name"), str):
                if not parts:
                    parts.append(attr)

            # Get other relevant attributes
            if isinstance(
                attr := bound_node.node().get_attr(key="child_identifier"), str
            ):
                parts.append(f"child={attr}")

            if isinstance(attr := bound_node.node().get_attr(key="link_type"), int):
                parts.append(f"link_type={attr}")

            if parts:
                label = " ".join(parts)
            elif isinstance(uuid := bound_node.node().get_attr(key="uuid"), int):
                label = f"node@{uuid}"
            else:
                label = repr(bound_node.node())

            return label

        def render(bound_node: BoundNode, prefix: str) -> None:
            child_edges: list[Any] = []

            def collect(ctx, edge):
                ctx.append(edge)

            EdgeComposition.visit_children_edges(
                bound_node=bound_node, ctx=child_edges, f=collect
            )

            # Build list of (display_name, edge) tuples
            edges_to_render = []
            for edge in child_edges:
                edge_name = EdgeComposition.get_name(edge=edge.edge())

                # Skip implements_ edges
                if edge_name.startswith("implements_"):
                    continue

                # Get child node to check for special attributes
                child_node = edge.edge().target()
                child_bound = edge.g().bind(node=child_node)

                # For MakeChild nodes, use child_identifier attribute as name
                if isinstance(
                    child_id := child_bound.node().get_attr(key="child_identifier"), str
                ):
                    display_name = child_id
                # For Reference chains, use the identifier
                elif edge_name:  # lhs/rhs etc
                    display_name = edge_name
                else:
                    # Use "_" for unnamed children
                    display_name = "_"

                edges_to_render.append((display_name, edge))

            edges_to_render.sort(key=lambda item: item[0])

            count = len(edges_to_render)
            for idx, (display_name, bound_edge) in enumerate(edges_to_render):
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
                    f"{prefix}{connector} [{display_name}] {child_label}",
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
    def create(typegraph: TypeGraph, type_identifier: str) -> "BoundNode":
        return typegraph.instantiate(type_identifier=type_identifier)

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
                # Use "_" for unnamed children
                display_name = edge_name if edge_name else "_"
                edge_label = f"{EdgeComposition.__name__}:{display_name}"
                node_label = get_node_label(child_bound)
                print(f"{prefix}{connector} [{edge_label}] {node_label}", file=stream)
                child_prefix = prefix + ("    " if is_last else "│   ")
                render(child_bound, child_prefix)

        print(get_node_label(root), file=stream)
        render(root, "")

        return stream.getvalue()
