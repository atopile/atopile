import io
import logging

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph

logger = logging.getLogger(__name__)


class GraphRenderer:
    @staticmethod
    def _node_key(bound_node: graph.BoundNode) -> int:
        """Get stable UUID for a node (used for cycle detection and caching)."""
        return bound_node.node().get_uuid()

    @staticmethod
    def _collect_children(bound_node: graph.BoundNode) -> list:
        """Collect all composition edge children of a node."""
        edges: list[graph.BoundEdge] = []

        def collect(ctx: list[graph.BoundEdge], edge: graph.BoundEdge) -> None:
            ctx.append(edge)

        fbrk.EdgeComposition.visit_children_edges(
            bound_node=bound_node, ctx=edges, f=collect
        )
        return edges

    @staticmethod
    def _collect_trait_edges(bound_node: graph.BoundNode) -> list:
        """Collect all trait edges of a node."""
        edges: list[graph.BoundEdge] = []

        def collect(ctx, edge):
            ctx.append(edge)

        fbrk.EdgeTrait.visit_trait_instance_edges(
            bound_node=bound_node, ctx=edges, f=collect
        )
        return edges

    @staticmethod
    def _collect_pointer_edges(bound_node: graph.BoundNode) -> list:
        """Collect all pointer edges of a node."""
        edges: list[graph.BoundEdge] = []

        def collect(ctx, edge):
            ctx.append(edge)

        fbrk.EdgePointer.visit_pointed_edges(
            bound_node=bound_node, ctx=edges, f=collect
        )
        return edges

    @staticmethod
    def _collect_connection_edges(bound_node: graph.BoundNode) -> list:
        """Collect all interface connection edges of a node."""
        edges: list[graph.BoundEdge] = []

        def collect(ctx: list[graph.BoundEdge], edge: graph.BoundEdge) -> None:
            ctx.append(edge)

        fbrk.EdgeInterfaceConnection.visit_connected_edges(
            bound_node=bound_node, ctx=edges, f=collect
        )
        return edges

    @staticmethod
    def render(
        root: graph.BoundNode,
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
            show_connections: If True, also show interface connection edges
                (default: False)
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
            fbrk.EdgeComposition.get_tid(): "Comp",
            fbrk.EdgeType.get_tid(): "Type",
            fbrk.EdgePointer.get_tid(): "Ptr",
            fbrk.EdgeInterfaceConnection.get_tid(): "Conn",
            fbrk.EdgeOperand.get_tid(): "Op",
        }
        # Trait edges are identified by checking EdgeTrait.is_instance()

        root_bound = root

        # Alias for cleaner code
        node_key = GraphRenderer._node_key
        collect_children = GraphRenderer._collect_children
        collect_trait_edges = GraphRenderer._collect_trait_edges
        collect_pointer_edges = GraphRenderer._collect_pointer_edges
        collect_connection_edges = GraphRenderer._collect_connection_edges

        def get_node_name(bound_node: graph.BoundNode) -> str:
            """Get just the node name (not the full label with type)."""
            key = node_key(bound_node)
            if key in node_names:
                return node_names[key]
            # Try direct name attribute first
            if isinstance(name := bound_node.node().get_attr(key="name"), str):
                node_names[key] = name
                return name
            # Try getting name from parent composition edge
            parent_edge = fbrk.EdgeComposition.get_parent_edge(bound_node=bound_node)
            if parent_edge is not None:
                edge_name = fbrk.EdgeComposition.get_name(edge=parent_edge.edge())
                if edge_name:
                    node_names[key] = edge_name
                    return edge_name
            # Fallback to showing the node id
            fallback_name = f"<node@{key}>"
            node_names[key] = fallback_name
            return fallback_name

        # Cache for type names
        type_names: dict[int, str | None] = {}

        def get_type_name(bound_node: graph.BoundNode) -> str | None:
            """Get the type name of a node (e.g., 'Electrical', 'is_module')."""
            key = node_key(bound_node)
            if key in type_names:
                return type_names[key]

            type_name = None
            try:
                type_edge = fbrk.EdgeType.get_type_edge(bound_node=bound_node)
                if type_edge is not None:
                    type_node = fbrk.EdgeType.get_type_node(edge=type_edge.edge())
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

        def get_node_label(bound_node: graph.BoundNode) -> str:
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

        def get_sorted_children(bound_node: graph.BoundNode) -> list:
            """Get children sorted by target type name, then edge type.

            Returns: list of (edge_name, edge_type_name, target_type, target_bound)
            """
            children = []
            # Composition edges
            for edge in collect_children(bound_node):
                edge_name = fbrk.EdgeComposition.get_name(edge=edge.edge())
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
                    other_node = fbrk.EdgeInterfaceConnection.get_other_connected_node(
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

        def count_new_nodes(
            bound_node: graph.BoundNode, already_counted: set[int]
        ) -> int:
            """
            Count nodes in subtree that haven't been counted yet.
            Returns 0 for nodes already in already_counted.
            """
            seen: set[int] = set(already_counted)  # Copy to avoid modifying original

            def count(node: graph.BoundNode) -> int:
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
            children: list[tuple[str, str, str, graph.BoundNode]],
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
            bound_node: graph.BoundNode,
            prefix: str,
            path: list[tuple[int, str]] | None = None,
            edge_name: str | None = None,
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
