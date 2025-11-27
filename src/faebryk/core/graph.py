# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import io
import logging
from typing import Any

from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.faebryk.node_type import EdgeType
from faebryk.core.zig.gen.faebryk.operand import EdgeOperand
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import (
    BFSPath,
    BoundEdge,
    BoundNode,
    Edge,
    GraphView,
    Node,
)

logger = logging.getLogger(__name__)


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

            if isinstance(attr := bound_node.node().get_attr(key="edge_type"), int):
                parts.append(f"edge_type={attr}")

            if isinstance(attr := bound_node.node().get_attr(key="directional"), bool):
                parts.append(f"directional={attr}")

            if isinstance(edge_name := bound_node.node().get_attr(key="name"), str):
                if not parts or parts[0] != edge_name:
                    parts.append(f"edge_name={edge_name}")

            if isinstance(attr := bound_node.node().get_attr(key="link_types"), str):
                parts.append(f"link_types={attr}")

            if isinstance(
                attr := bound_node.node().get_attr(key="link_type_count"), int
            ):
                parts.append(f"link_type_count={attr}")

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
                if isinstance(edge_name, str) and edge_name.startswith("implements_"):
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
    def _node_key(bound_node: BoundNode) -> int:
        """Get stable UUID for a node (used for cycle detection and caching)."""
        return bound_node.node().get_uuid()

    @staticmethod
    def _collect_children(bound_node: BoundNode) -> list:
        """Collect all composition edge children of a node."""
        edges: list[Any] = []

        def collect(ctx, edge):
            ctx.append(edge)

        EdgeComposition.visit_children_edges(
            bound_node=bound_node, ctx=edges, f=collect
        )
        return edges

    @staticmethod
    def _build_node_counts(root_bound: BoundNode) -> dict[int, int]:
        """
        Build a mapping of node UUID -> total node count (node + descendants).

        This is shared logic used by both count_nodes() and render().
        """
        counts: dict[int, int] = {}
        visited: set[int] = set()

        def count(bound_node: BoundNode) -> int:
            key = InstanceGraphFunctions._node_key(bound_node)
            if key in counts:
                return counts[key]
            if key in visited:
                return 0  # Cycle, don't count again

            visited.add(key)
            total = 1  # Count this node
            for edge in InstanceGraphFunctions._collect_children(bound_node):
                child_bound = edge.g().bind(node=edge.edge().target())
                total += count(child_bound)

            counts[key] = total
            return total

        count(root_bound)
        return counts

    @staticmethod
    def count_nodes(root: BoundNode) -> int:
        """
        Count the total number of nodes in the instance tree.

        Args:
            root: A BoundNode instance

        Returns:
            Total node count (including root)
        """
        counts = InstanceGraphFunctions._build_node_counts(root)
        root_key = InstanceGraphFunctions._node_key(root)
        return counts.get(root_key, 0)

    @staticmethod
    def render(root: BoundNode) -> str:
        """
        Render an instance graph as ASCII tree.

        Args:
            root: A BoundNode instance

        Returns:
            ASCII tree representation showing type names and instance names
        """

        stream = io.StringIO()
        visited: set[int] = set()
        labels: dict[int, str] = {}

        # Build edge type ID to name mapping
        edge_type_names: dict[int, str] = {
            EdgeComposition.get_tid(): "Comp",
            EdgeType.get_tid(): "Type",
            EdgePointer.get_tid(): "Ptr",
            EdgeInterfaceConnection.get_tid(): "Conn",
            EdgeOperand.get_tid(): "Op",
        }

        root_bound = root

        # Alias for cleaner code
        node_key = InstanceGraphFunctions._node_key
        collect_children = InstanceGraphFunctions._collect_children

        def get_node_label(bound_node: BoundNode) -> str:
            """Build label showing type name and instance name."""
            if (key := node_key(bound_node)) in labels:
                return labels[key]

            parts = []

            # Get type name from the type edge
            try:
                type_edge = EdgeType.get_type_edge(bound_node=bound_node)
                if type_edge is not None:
                    type_node = EdgeType.get_type_node(edge=type_edge.edge())
                    type_bound = type_edge.g().bind(node=type_node)
                    if isinstance(
                        type_name := type_bound.node().get_attr(key="type_identifier"),
                        str,
                    ):
                        parts.append(type_name)
            except Exception:
                pass

            # Get instance name
            if isinstance(name := bound_node.node().get_attr(key="name"), str):
                if parts:
                    parts.append(f'"{name}"')
                else:
                    parts.append(name)

            if parts:
                label = " ".join(parts)
            else:
                # Fallback to showing the node id
                label = f"<node@{id(bound_node.node())}>"

            labels[key] = label
            return label

        def get_edge_type_name(edge) -> str:
            """Get human-readable edge type name."""
            edge_tid = edge.edge_type()
            return edge_type_names.get(edge_tid, f"?{edge_tid}")

        # Pre-compute node counts using shared logic
        node_counts = InstanceGraphFunctions._build_node_counts(root_bound)
        root_count = node_counts.get(node_key(root_bound), 0)

        def render_node(bound_node: BoundNode, prefix: str) -> None:
            key = node_key(bound_node)
            if key in visited:
                # Show which node the cycle points to
                cycle_label = labels.get(key, f"<node@{key}>")
                print(f"{prefix}(cycle → {cycle_label})", file=stream)
                return

            visited.add(key)
            children = []
            for edge in collect_children(bound_node):
                edge_name = EdgeComposition.get_name(edge=edge.edge())
                edge_type_name = get_edge_type_name(edge.edge())
                children.append((edge_name, edge, edge_type_name))

            children.sort(key=lambda item: item[0])

            total = len(children)
            for idx, (edge_name, bound_edge, edge_type_name) in enumerate(children):
                is_last = idx == total - 1
                connector = "└──" if is_last else "├──"
                child_bound = bound_edge.g().bind(node=bound_edge.edge().target())
                display_name = edge_name if edge_name else "_"
                node_label = get_node_label(child_bound)
                child_count = node_counts.get(node_key(child_bound), 0)
                # Format: [EdgeType] name: TypeName (N)
                print(
                    f"{prefix}{connector} [{edge_type_name}] {display_name}: "
                    f"{node_label} ({child_count})",
                    file=stream,
                )
                child_prefix = prefix + ("    " if is_last else "│   ")
                render_node(child_bound, child_prefix)

        print(f"{get_node_label(root_bound)} ({root_count})", file=stream)
        render_node(root_bound, "")

        return stream.getvalue()


__all__ = [
    "TypeGraph",
    "BFSPath",
    "BoundEdge",
    "BoundNode",
    "Edge",
    "GraphView",
    "Node",
]
