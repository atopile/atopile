import io
import logging
from typing import Callable

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
    def _collect_operand_edges(bound_node: graph.BoundNode) -> list:
        """Collect all operand edges of a node."""
        edges: list[graph.BoundEdge] = []

        def collect(ctx: list[graph.BoundEdge], edge: graph.BoundEdge) -> None:
            ctx.append(edge)

        fbrk.EdgeOperand.visit_operand_edges(
            bound_node=bound_node, ctx=edges, f=collect
        )

        return edges

    @staticmethod
    def _get_type_name(bound_node: graph.BoundNode) -> str | None:
        """Get the type name of a node (e.g., 'Electrical', 'is_module')."""
        try:
            type_edge = fbrk.EdgeType.get_type_edge(bound_node=bound_node)
            if type_edge is not None:
                type_node = fbrk.EdgeType.get_type_node(edge=type_edge.edge())
                type_bound = type_edge.g().bind(node=type_node)
                if isinstance(
                    tn := type_bound.node().get_attr(key="type_identifier"),
                    str,
                ):
                    return tn
        except Exception:
            pass
        return None

    @staticmethod
    def _has_interface_trait(bound_node: graph.BoundNode) -> bool:
        """Check if a node has the is_interface trait."""
        edges: list[graph.BoundEdge] = []

        def collect(ctx, edge):
            ctx.append(edge)

        fbrk.EdgeTrait.visit_trait_instance_edges(
            bound_node=bound_node, ctx=edges, f=collect
        )
        for edge in edges:
            target_bound = edge.g().bind(node=edge.edge().target())
            if GraphRenderer._get_type_name(target_bound) == "is_interface":
                return True
        return False

    @staticmethod
    def _contains_interface(
        bound_node: graph.BoundNode,
        cache: dict[int, bool],
        visited: set[int] | None = None,
    ) -> bool:
        """Check if a node or any of its composition descendants have is_interface."""
        key = GraphRenderer._node_key(bound_node)
        if key in cache:
            return cache[key]

        if visited is None:
            visited = set()
        if key in visited:
            return False
        visited.add(key)

        if GraphRenderer._has_interface_trait(bound_node):
            cache[key] = True
            return True

        for edge in GraphRenderer._collect_children(bound_node):
            child_bound = edge.g().bind(node=edge.edge().target())
            if GraphRenderer._contains_interface(child_bound, cache, visited):
                cache[key] = True
                return True

        cache[key] = False
        return False

    class _InternalRenderer:
        def __init__(self, root: graph.BoundNode):
            self.root = root
            self.stream = io.StringIO()
            self.visited: set[int] = set()
            self.labels: dict[int, str] = {}
            self.node_names: dict[int, str] = {}
            self.first_rendered_at: dict[int, str] = {}
            self.type_names: dict[int, str | None] = {}
            self.edge_type_names = {
                fbrk.EdgeComposition.get_tid(): "Comp",
                fbrk.EdgeType.get_tid(): "Type",
                fbrk.EdgePointer.get_tid(): "Ptr",
                fbrk.EdgeInterfaceConnection.get_tid(): "Conn",
                fbrk.EdgeOperand.get_tid(): "Op",
            }

        def get_type_name(self, bound_node: graph.BoundNode) -> str | None:
            key = GraphRenderer._node_key(bound_node)
            if key in self.type_names:
                return self.type_names[key]
            name = GraphRenderer._get_type_name(bound_node)
            self.type_names[key] = name
            return name

        def get_node_name(self, bound_node: graph.BoundNode) -> str:
            key = GraphRenderer._node_key(bound_node)
            if key in self.node_names:
                return self.node_names[key]
            if isinstance(name := bound_node.node().get_attr(key="name"), str):
                self.node_names[key] = name
                return name
            parent_edge = fbrk.EdgeComposition.get_parent_edge(bound_node=bound_node)
            if parent_edge is not None:
                edge_name = fbrk.EdgeComposition.get_name(edge=parent_edge.edge())
                if edge_name:
                    self.node_names[key] = edge_name
                    return edge_name
            fallback_name = f"<node@{key}>"
            self.node_names[key] = fallback_name
            return fallback_name

        def get_node_label(self, bound_node: graph.BoundNode) -> str:
            key = GraphRenderer._node_key(bound_node)
            if key in self.labels:
                return self.labels[key]
            parts = []
            if type_name := self.get_type_name(bound_node):
                parts.append(type_name)
            if isinstance(name := bound_node.node().get_attr(key="name"), str):
                parts.append(f'"{name}"' if parts else name)
            label = " ".join(parts) if parts else f"<node@{id(bound_node.node())}>"
            self.labels[key] = label
            return label

        def get_edge_type_name(self, edge: graph.Edge) -> str:
            return self.edge_type_names.get(edge.edge_type(), f"?{edge.edge_type()}")

        def count_new_nodes(
            self,
            bound_node: graph.BoundNode,
            already_counted: set[int],
            get_children_func: Callable[[graph.BoundNode], list],
        ) -> int:
            seen = set(already_counted)

            def count(node: graph.BoundNode) -> int:
                key = GraphRenderer._node_key(node)
                if key in seen:
                    return 0
                seen.add(key)
                total = 1
                for _, _, _, child_bound in get_children_func(node):
                    total += count(child_bound)
                return total

            return count(bound_node)

        def print_child_line(
            self,
            prefix: str,
            is_last: bool,
            edge_type_name: str,
            display_name: str,
            node_label: str,
            child_key: int,
            suffix: str,
        ) -> None:
            connector = "└──" if is_last else "├──"
            print(
                f"{prefix}{connector} [{edge_type_name}] {display_name}: "
                f"{node_label} {child_key:x} {suffix}",
                file=self.stream,
            )

        def render_node(
            self,
            bound_node: graph.BoundNode,
            prefix: str,
            get_children_func: Callable[[graph.BoundNode], list],
            path: list[tuple[int, str]],
            edge_name: str | None = None,
            show_cycle_length: bool = True,
        ) -> None:
            key = GraphRenderer._node_key(bound_node)
            current_name = self.get_node_name(bound_node)
            display_name = edge_name if edge_name else current_name

            if key in self.visited:
                path_keys = [k for k, _ in path]
                if key in path_keys:
                    cycle_start_idx = path_keys.index(key)
                    cycle_path = path[cycle_start_idx:] + [(key, display_name)]
                    info = " → ".join(name for _, name in cycle_path)
                    suffix = f", length={len(cycle_path)}" if show_cycle_length else ""
                    print(f"{prefix}    (cycle: {info}{suffix})", file=self.stream)
                return

            self.visited.add(key)
            self.first_rendered_at[key] = display_name
            new_path = path + [(key, display_name)]

            children = get_children_func(bound_node)
            total = len(children)
            for idx, (e_name, e_type, _, c_bound) in enumerate(children):
                is_last = idx == total - 1
                c_display_name = e_name if e_name else "_"
                c_label = self.get_node_label(c_bound)
                c_key = GraphRenderer._node_key(c_bound)
                c_prefix = prefix + ("    " if is_last else "│   ")

                if c_key in self.visited:
                    orig = self.first_rendered_at.get(c_key, "?")
                    self.print_child_line(
                        prefix,
                        is_last,
                        e_type,
                        c_display_name,
                        c_label,
                        c_key,
                        f"(same as {orig})",
                    )
                else:
                    count = self.count_new_nodes(
                        c_bound, self.visited, get_children_func
                    )
                    self.print_child_line(
                        prefix,
                        is_last,
                        e_type,
                        c_display_name,
                        c_label,
                        c_key,
                        f"({count})",
                    )

                self.render_node(
                    c_bound,
                    c_prefix,
                    get_children_func,
                    new_path,
                    edge_name=c_display_name,
                    show_cycle_length=show_cycle_length,
                )

    @staticmethod
    def render(
        root: graph.BoundNode,
        show_traits: bool = True,
        show_pointers: bool = False,
        show_connections: bool = True,
        show_operands: bool = False,
        filter_types: list[str] | None = None,
    ) -> str:
        """
        Render an instance graph as ASCII tree.
        """
        r = GraphRenderer._InternalRenderer(root)

        def get_children(bound_node: graph.BoundNode) -> list:
            children = []
            for edge in GraphRenderer._collect_children(bound_node):
                target_bound = edge.g().bind(node=edge.edge().target())
                children.append(
                    (
                        fbrk.EdgeComposition.get_name(edge=edge.edge()),
                        r.get_edge_type_name(edge.edge()),
                        r.get_type_name(target_bound) or "",
                        target_bound,
                    )
                )

            if show_traits:
                for edge in GraphRenderer._collect_trait_edges(bound_node):
                    target_bound = edge.g().bind(node=edge.edge().target())
                    children.append(
                        (
                            "→",
                            "Trait",
                            r.get_type_name(target_bound) or "",
                            target_bound,
                        )
                    )

            if show_pointers:
                for edge in GraphRenderer._collect_pointer_edges(bound_node):
                    target_bound = edge.g().bind(node=edge.edge().target())
                    children.append(
                        ("→", "Ptr", r.get_type_name(target_bound) or "", target_bound)
                    )

            if show_connections:
                for edge in GraphRenderer._collect_connection_edges(bound_node):
                    other = fbrk.EdgeInterfaceConnection.get_other_connected_node(
                        edge=edge.edge(), node=bound_node.node()
                    )
                    if other is not None and other != bound_node.node():
                        target_bound = edge.g().bind(node=other)
                        children.append(
                            (
                                r.get_node_name(target_bound),
                                "Conn",
                                r.get_type_name(target_bound) or "",
                                target_bound,
                            )
                        )

            if show_operands:
                for edge in GraphRenderer._collect_operand_edges(bound_node):
                    target_bound = edge.g().bind(node=edge.edge().target())
                    children.append(
                        ("→", "Op", r.get_type_name(target_bound) or "", target_bound)
                    )

            children.sort(key=lambda item: (item[2], item[1]))
            return children

        root_key = GraphRenderer._node_key(root)
        if filter_types:
            type_filter_set = set(filter_types)
            children = get_children(root)
            matching = [c for c in children if c[2] in type_filter_set]

            if not matching:
                print(
                    f"{r.get_node_label(root)} {root_key:x} "
                    f"(no children matching: {filter_types})",
                    file=r.stream,
                )
            else:
                print(
                    f"{r.get_node_label(root)} {root_key:x} "
                    f"(filtered to {len(matching)} children)",
                    file=r.stream,
                )
                r.render_node(root, "", lambda _: matching, [], show_cycle_length=True)
        else:
            count = r.count_new_nodes(root, set(), get_children)
            print(f"{r.get_node_label(root)} {root_key:x} ({count})", file=r.stream)
            r.render_node(root, "", get_children, [], show_cycle_length=True)

        return r.stream.getvalue()

    @staticmethod
    def render_interfaces(root: graph.BoundNode) -> str:
        """
        Render only the interface structure of the graph.
        """
        r = GraphRenderer._InternalRenderer(root)
        cache: dict[int, bool] = {}

        def get_children(bound_node: graph.BoundNode) -> list:
            children = []
            for edge in GraphRenderer._collect_children(bound_node):
                target_bound = edge.g().bind(node=edge.edge().target())
                if GraphRenderer._contains_interface(target_bound, cache):
                    children.append(
                        (
                            fbrk.EdgeComposition.get_name(edge=edge.edge()),
                            "Comp",
                            r.get_type_name(target_bound) or "",
                            target_bound,
                        )
                    )

            for edge in GraphRenderer._collect_connection_edges(bound_node):
                other = fbrk.EdgeInterfaceConnection.get_other_connected_node(
                    edge=edge.edge(), node=bound_node.node()
                )
                if other is not None and other != bound_node.node():
                    target_bound = edge.g().bind(node=other)
                    children.append(
                        (
                            r.get_node_name(target_bound),
                            "Conn",
                            r.get_type_name(target_bound) or "",
                            target_bound,
                        )
                    )

            children.sort(key=lambda item: (item[2], item[1]))
            return children

        root_key = GraphRenderer._node_key(root)
        count = r.count_new_nodes(root, set(), get_children)
        print(f"{r.get_node_label(root)} {root_key:x} ({count})", file=r.stream)
        r.render_node(root, "", get_children, [], show_cycle_length=False)

        return r.stream.getvalue()
