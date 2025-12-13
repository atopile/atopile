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
from faebryk.core.zig.gen.faebryk.trait import EdgeTrait
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
    def _collect_trait_edges(bound_node: BoundNode) -> list:
        """Collect all trait edges of a node."""
        edges: list[Any] = []

        def collect(ctx, edge):
            ctx.append(edge)

        EdgeTrait.visit_trait_instance_edges(
            bound_node=bound_node, ctx=edges, f=collect
        )
        return edges

    @staticmethod
    def _collect_pointer_edges(bound_node: BoundNode) -> list:
        """Collect all pointer edges of a node."""
        edges: list[Any] = []

        def collect(ctx, edge):
            ctx.append(edge)

        EdgePointer.visit_pointed_edges(bound_node=bound_node, ctx=edges, f=collect)
        return edges

    @staticmethod
    def _collect_connection_edges(bound_node: BoundNode) -> list:
        """Collect all interface connection edges of a node."""
        edges: list[Any] = []

        def collect(ctx, edge):
            ctx.append(edge)

        EdgeInterfaceConnection.visit_connected_edges(
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
            # Check if already visited FIRST - return 0 to avoid double counting
            if key in visited:
                return 0

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
    def render(
        root: BoundNode,
        show_traits: bool = True,
        show_pointers: bool = False,
        show_connections: bool = True,
        filter_types: list[str] | None = None,
    ) -> str:
        """
        Render an instance graph as ASCII tree.

        Args:
            root: A BoundNode instance
            show_traits: If True, also show trait edges (default: False)
            show_pointers: If True, also show pointer edges (default: False)
            show_connections: If True, also show interface connection edges (default: False)
            filter_types: If provided, only render subtrees under children
                         with these type names (e.g., ["Electrical", "is_module"])

        Returns:
            ASCII tree representation showing type names and instance names
        """

        stream = io.StringIO()
        visited: set[int] = set()
        labels: dict[int, str] = {}
        node_names: dict[int, str] = {}
        # Track where each node was first rendered (for "already rendered" message)
        first_rendered_at: dict[int, str] = {}

        # Build edge type ID to name mapping
        edge_type_names: dict[int, str] = {
            EdgeComposition.get_tid(): "Comp",
            EdgeType.get_tid(): "Type",
            EdgePointer.get_tid(): "Ptr",
            EdgeInterfaceConnection.get_tid(): "Conn",
            EdgeOperand.get_tid(): "Op",
        }
        # Trait edges are identified by checking EdgeTrait.is_instance()

        root_bound = root

        # Alias for cleaner code
        node_key = InstanceGraphFunctions._node_key
        collect_children = InstanceGraphFunctions._collect_children
        collect_trait_edges = InstanceGraphFunctions._collect_trait_edges
        collect_pointer_edges = InstanceGraphFunctions._collect_pointer_edges
        collect_connection_edges = InstanceGraphFunctions._collect_connection_edges

        def get_node_name(bound_node: BoundNode) -> str:
            """Get just the node name (not the full label with type)."""
            key = node_key(bound_node)
            if key in node_names:
                return node_names[key]
            # Try direct name attribute first
            if isinstance(name := bound_node.node().get_attr(key="name"), str):
                node_names[key] = name
                return name
            # Try getting name from parent composition edge
            parent_edge = EdgeComposition.get_parent_edge(bound_node=bound_node)
            if parent_edge is not None:
                edge_name = EdgeComposition.get_name(edge=parent_edge.edge())
                if edge_name:
                    node_names[key] = edge_name
                    return edge_name
            # Fallback to showing the node id
            fallback_name = f"<node@{key}>"
            node_names[key] = fallback_name
            return fallback_name

        # Cache for type names
        type_names: dict[int, str | None] = {}

        def get_type_name(bound_node: BoundNode) -> str | None:
            """Get the type name of a node (e.g., 'Electrical', 'is_module')."""
            key = node_key(bound_node)
            if key in type_names:
                return type_names[key]

            type_name = None
            try:
                type_edge = EdgeType.get_type_edge(bound_node=bound_node)
                if type_edge is not None:
                    type_node = EdgeType.get_type_node(edge=type_edge.edge())
                    type_bound = type_edge.g().bind(node=type_node)
                    if isinstance(
                        tn := type_bound.node().get_attr(key="type_identifier"),
                        str,
                    ):
                        type_name = tn
            except Exception:
                pass

            type_names[key] = type_name
            return type_name

        def get_node_label(bound_node: BoundNode) -> str:
            """Build label showing type name and instance name."""
            if (key := node_key(bound_node)) in labels:
                return labels[key]

            parts = []

            # Get type name (reuse cached value)
            type_name = get_type_name(bound_node)
            if type_name:
                parts.append(type_name)

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

        def get_sorted_children(bound_node: BoundNode) -> list:
            """Get children sorted by target type name, then edge type.

            Returns: list of (edge_name, edge_type_name, target_type, target_bound)
            """
            children = []
            # Composition edges
            for edge in collect_children(bound_node):
                edge_name = EdgeComposition.get_name(edge=edge.edge())
                edge_type_name = get_edge_type_name(edge.edge())
                target_bound = edge.g().bind(node=edge.edge().target())
                target_type = get_type_name(target_bound) or ""
                children.append((edge_name, edge_type_name, target_type, target_bound))

            # Trait edges (if enabled)
            if show_traits:
                for edge in collect_trait_edges(bound_node):
                    target_bound = edge.g().bind(node=edge.edge().target())
                    target_type = get_type_name(target_bound) or ""
                    children.append(("→", "Trait", target_type, target_bound))

            # Pointer edges (if enabled)
            if show_pointers:
                for edge in collect_pointer_edges(bound_node):
                    target_bound = edge.g().bind(node=edge.edge().target())
                    target_type = get_type_name(target_bound) or ""
                    children.append(("→", "Ptr", target_type, target_bound))

            # Connection edges (if enabled)
            if show_connections:
                for edge in collect_connection_edges(bound_node):
                    # Use get_other_connected_node since connections are bidirectional
                    other_node = EdgeInterfaceConnection.get_other_connected_node(
                        edge=edge.edge(), node=bound_node.node()
                    )
                    # Skip self-connections (always present on interfaces)
                    if other_node is not None and other_node != bound_node.node():
                        target_bound = edge.g().bind(node=other_node)
                        target_type = get_type_name(target_bound) or ""
                        # Use target node's name to show what we're connected to
                        conn_name = get_node_name(target_bound)
                        children.append((conn_name, "Conn", target_type, target_bound))

            # Sort by target type name first, then edge type (Comp before Ptr/Trait)
            children.sort(key=lambda item: (item[2], item[1]))
            return children

        def count_new_nodes(bound_node: BoundNode, already_counted: set[int]) -> int:
            """
            Count nodes in subtree that haven't been counted yet.
            Returns 0 for nodes already in already_counted.
            """
            seen: set[int] = set(already_counted)  # Copy to avoid modifying original

            def count(node: BoundNode) -> int:
                key = node_key(node)
                if key in seen:
                    return 0  # Already counted
                seen.add(key)

                total = 1  # Count this node
                for _, _, _, child_bound in get_sorted_children(node):
                    total += count(child_bound)
                return total

            return count(bound_node)

        def print_child_line(
            prefix: str,
            is_last: bool,
            edge_type_name: str,
            display_name: str,
            node_label: str,
            child_key: int,
            suffix: str,
        ) -> None:
            """Print a single child line with consistent formatting."""
            connector = "└──" if is_last else "├──"
            print(
                f"{prefix}{connector} [{edge_type_name}] {display_name}: "
                f"{node_label} {child_key:x} {suffix}",
                file=stream,
            )

        def render_child_list(
            children: list[tuple[str, str, str, Any]],
            prefix: str,
            path: list[tuple[int, str]],
        ) -> None:
            """Render a list of children, handling visited/shared nodes."""
            total = len(children)
            for idx, (edge_name, edge_type_name, _, child_bound) in enumerate(children):
                is_last = idx == total - 1
                child_display_name = edge_name if edge_name else "_"
                node_label = get_node_label(child_bound)
                child_key = node_key(child_bound)
                child_prefix = prefix + ("    " if is_last else "│   ")

                if child_key in visited:
                    # Shared node - show reference to original
                    original_name = first_rendered_at.get(child_key, "?")
                    print_child_line(
                        prefix,
                        is_last,
                        edge_type_name,
                        child_display_name,
                        node_label,
                        child_key,
                        f"(same as {original_name})",
                    )
                else:
                    # New node - show count
                    child_count = count_new_nodes(child_bound, visited)
                    print_child_line(
                        prefix,
                        is_last,
                        edge_type_name,
                        child_display_name,
                        node_label,
                        child_key,
                        f"({child_count})",
                    )

                render_node(
                    child_bound, child_prefix, path, edge_name=child_display_name
                )

        def render_node(
            bound_node: BoundNode,
            prefix: str,
            path: list[tuple[int, str]] = None,
            edge_name: str = None,
        ) -> None:
            if path is None:
                path = []

            key = node_key(bound_node)
            current_node_name = get_node_name(bound_node)
            display_name = edge_name if edge_name else current_node_name

            if key in visited:
                # Check if this is a real cycle (in current path)
                path_keys = [k for k, _ in path]
                if key in path_keys:
                    # Real cycle - node is an ancestor in current path
                    cycle_start_idx = path_keys.index(key)
                    cycle_path = path[cycle_start_idx:] + [(key, display_name)]
                    cycle_path_names = [name for _, name in cycle_path]
                    cycle_info = " → ".join(cycle_path_names)
                    cycle_length = len(cycle_path)
                    print(
                        f"{prefix}    (cycle: {cycle_info}, length={cycle_length})",
                        file=stream,
                    )
                return

            visited.add(key)
            first_rendered_at[key] = display_name
            path = path + [(key, display_name)]

            render_child_list(get_sorted_children(bound_node), prefix, path)

        # Compute root count and render
        root_key = node_key(root_bound)

        if filter_types:
            # Filter mode: find matching children and render only those subtrees
            type_filter_set = set(filter_types)
            children = get_sorted_children(root_bound)

            matching = [
                (name, edge, etype, ttype)
                for name, edge, etype, ttype in children
                if ttype in type_filter_set
            ]

            if not matching:
                print(
                    f"{get_node_label(root_bound)} {root_key:x} "
                    f"(no children matching types: {filter_types})",
                    file=stream,
                )
            else:
                print(
                    f"{get_node_label(root_bound)} {root_key:x} "
                    f"(filtered to {len(matching)} children)",
                    file=stream,
                )
                render_child_list(matching, "", [])
        else:
            # Normal mode: render entire tree
            root_count = count_new_nodes(root_bound, set())
            print(
                f"{get_node_label(root_bound)} {root_key:x} ({root_count})", file=stream
            )
            render_node(root_bound, "", [], edge_name=None)

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


def test_graph_garbage_collection(
    n: int = 10**5,
    trim: bool = True,
    trace_python_alloc: bool = False,
):
    import ctypes
    import gc
    import os
    import sys

    import psutil

    if trace_python_alloc:
        # Helps distinguish "RSS didn't drop" from "Python is still holding objects".
        # Note: this measures Python allocations, not Zig allocations.
        import tracemalloc

        tracemalloc.start()

    mem = psutil.Process().memory_info().rss

    def _get_mem_diff() -> int:
        nonlocal mem
        old_mem = mem
        mem = psutil.Process().memory_info().rss
        return mem - old_mem

    # pre measure memory
    g = GraphView.create()

    for _ in range(n):
        g.insert_node(node=Node.create())

    mem_create = _get_mem_diff()

    g.destroy()

    mem_destroy = _get_mem_diff()

    # run gc

    gc.collect()

    mem_gc = _get_mem_diff()

    if trace_python_alloc:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        try:
            blocks = sys.getallocatedblocks()
        except AttributeError:
            blocks = None
        print("Py tracemalloc current: ", current / 1024 / 1024, "MB")
        print("Py tracemalloc peak: ", peak / 1024 / 1024, "MB")
        if blocks is not None:
            print("Py allocated blocks: ", blocks)

    # On glibc (common on Linux), freed memory is often kept in the process heap
    # and not returned to the OS immediately, which makes RSS-based "leak" tests
    # look worse than reality. `malloc_trim(0)` asks glibc to release free heap
    # pages back to the OS. This is a no-op on non-glibc allocators.
    mem_trim = 0
    try:
        if trim and os.name == "posix":
            libc = ctypes.CDLL(None)
            trimmer = getattr(libc, "malloc_trim", None)
            if trimmer is not None:
                trimmer.argtypes = [ctypes.c_size_t]
                trimmer.restype = ctypes.c_int
                trimmer(0)
                mem_trim = _get_mem_diff()
    except Exception as e:
        print("Failed to trim memory", e)
        pass

    mem_leaked = sum([mem_create, mem_destroy, mem_gc, mem_trim])

    print("N: ", n)
    print("Mem create: ", mem_create / 1024 / 1024, "MB")
    print("Mem destroy: ", mem_destroy / 1024 / 1024, "MB")
    print("Mem gc: ", mem_gc / 1024 / 1024, "MB")
    print("Mem trim: ", mem_trim / 1024 / 1024, "MB")
    print("Mem leaked: ", mem_leaked / 1024 / 1024, "MB")

    if trim:
        # This is RSS in *bytes*. After destroy+gc+trim we expect this to be small.
        assert mem_leaked < 2 * 1024 * 1024


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()
    typer.run(test_graph_garbage_collection)
