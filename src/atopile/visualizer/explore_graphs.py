"""
Explore graph structures of library modules.

Run with:
    python -m atopile.visualizer.explore_graphs

This script instantiates various library modules and analyzes their graph
structures to understand node/edge counts, types, and composition depths.
"""

import logging
from dataclasses import dataclass, field
from typing import Callable

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
from faebryk.core.graph_render import GraphRenderer
from faebryk.library import _F as F

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


@dataclass
class GraphMetrics:
    """Metrics collected from exploring a graph."""

    total_nodes: int = 0
    total_edges: int = 0
    composition_edges: int = 0
    trait_edges: int = 0
    pointer_edges: int = 0
    connection_edges: int = 0
    operand_edges: int = 0
    type_edges: int = 0
    max_depth: int = 0
    node_types: dict[str, int] = field(default_factory=dict)
    trait_types: dict[str, int] = field(default_factory=dict)


def count_edges_by_type(
    bound_node: graph.BoundNode, visited: set[int] | None = None
) -> dict[str, int]:
    """Count edges by type starting from a node."""
    if visited is None:
        visited = set()

    node_uuid = bound_node.node().get_uuid()
    if node_uuid in visited:
        return {}
    visited.add(node_uuid)

    counts: dict[str, int] = {
        "composition": 0,
        "trait": 0,
        "pointer": 0,
        "connection": 0,
        "operand": 0,
    }

    # Count composition edges and recurse
    comp_edges: list[graph.BoundEdge] = []

    def collect_comp(ctx: list, edge: graph.BoundEdge) -> None:
        ctx.append(edge)

    fbrk.EdgeComposition.visit_children_edges(
        bound_node=bound_node, ctx=comp_edges, f=collect_comp
    )
    counts["composition"] = len(comp_edges)

    for edge in comp_edges:
        child_bound = edge.g().bind(node=edge.edge().target())
        child_counts = count_edges_by_type(child_bound, visited)
        for k, v in child_counts.items():
            counts[k] = counts.get(k, 0) + v

    # Count trait edges
    trait_edges: list[graph.BoundEdge] = []

    def collect_trait(ctx: list, edge: graph.BoundEdge) -> None:
        ctx.append(edge)

    fbrk.EdgeTrait.visit_trait_instance_edges(
        bound_node=bound_node, ctx=trait_edges, f=collect_trait
    )
    counts["trait"] += len(trait_edges)

    # Count pointer edges
    ptr_edges: list[graph.BoundEdge] = []

    def collect_ptr(ctx: list, edge: graph.BoundEdge) -> None:
        ctx.append(edge)

    fbrk.EdgePointer.visit_pointed_edges(
        bound_node=bound_node, ctx=ptr_edges, f=collect_ptr
    )
    counts["pointer"] += len(ptr_edges)

    # Count connection edges
    conn_edges: list[graph.BoundEdge] = []

    def collect_conn(ctx: list, edge: graph.BoundEdge) -> None:
        ctx.append(edge)

    fbrk.EdgeInterfaceConnection.visit_connected_edges(
        bound_node=bound_node, ctx=conn_edges, f=collect_conn
    )
    counts["connection"] += len(conn_edges)

    # Count operand edges
    op_edges: list[graph.BoundEdge] = []

    def collect_op(ctx: list, edge: graph.BoundEdge) -> None:
        ctx.append(edge)

    fbrk.EdgeOperand.visit_operand_edges(bound_node=bound_node, ctx=op_edges, f=collect_op)
    counts["operand"] += len(op_edges)

    return counts


def measure_depth(bound_node: graph.BoundNode, visited: set[int] | None = None) -> int:
    """Measure the maximum composition depth from a node."""
    if visited is None:
        visited = set()

    node_uuid = bound_node.node().get_uuid()
    if node_uuid in visited:
        return 0
    visited.add(node_uuid)

    children: list[graph.BoundEdge] = []

    def collect(ctx: list, edge: graph.BoundEdge) -> None:
        ctx.append(edge)

    fbrk.EdgeComposition.visit_children_edges(
        bound_node=bound_node, ctx=children, f=collect
    )

    if not children:
        return 1

    max_child_depth = 0
    for edge in children:
        child_bound = edge.g().bind(node=edge.edge().target())
        child_depth = measure_depth(child_bound, visited)
        max_child_depth = max(max_child_depth, child_depth)

    return 1 + max_child_depth


def count_nodes(bound_node: graph.BoundNode, visited: set[int] | None = None) -> int:
    """Count total nodes reachable via composition edges."""
    if visited is None:
        visited = set()

    node_uuid = bound_node.node().get_uuid()
    if node_uuid in visited:
        return 0
    visited.add(node_uuid)

    count = 1
    children: list[graph.BoundEdge] = []

    def collect(ctx: list, edge: graph.BoundEdge) -> None:
        ctx.append(edge)

    fbrk.EdgeComposition.visit_children_edges(
        bound_node=bound_node, ctx=children, f=collect
    )

    for edge in children:
        child_bound = edge.g().bind(node=edge.edge().target())
        count += count_nodes(child_bound, visited)

    return count


def get_type_name(bound_node: graph.BoundNode) -> str | None:
    """Get the type name of a node."""
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


def collect_type_names(
    bound_node: graph.BoundNode, visited: set[int] | None = None
) -> dict[str, int]:
    """Collect all type names and their counts."""
    if visited is None:
        visited = set()

    node_uuid = bound_node.node().get_uuid()
    if node_uuid in visited:
        return {}
    visited.add(node_uuid)

    types: dict[str, int] = {}
    type_name = get_type_name(bound_node)
    if type_name:
        types[type_name] = types.get(type_name, 0) + 1

    children: list[graph.BoundEdge] = []

    def collect(ctx: list, edge: graph.BoundEdge) -> None:
        ctx.append(edge)

    fbrk.EdgeComposition.visit_children_edges(
        bound_node=bound_node, ctx=children, f=collect
    )

    for edge in children:
        child_bound = edge.g().bind(node=edge.edge().target())
        child_types = collect_type_names(child_bound, visited)
        for k, v in child_types.items():
            types[k] = types.get(k, 0) + v

    return types


def collect_trait_names(
    bound_node: graph.BoundNode, visited: set[int] | None = None
) -> dict[str, int]:
    """Collect all trait type names and their counts."""
    if visited is None:
        visited = set()

    node_uuid = bound_node.node().get_uuid()
    if node_uuid in visited:
        return {}
    visited.add(node_uuid)

    traits: dict[str, int] = {}

    # Get traits on this node
    trait_edges: list[graph.BoundEdge] = []

    def collect_trait(ctx: list, edge: graph.BoundEdge) -> None:
        ctx.append(edge)

    fbrk.EdgeTrait.visit_trait_instance_edges(
        bound_node=bound_node, ctx=trait_edges, f=collect_trait
    )

    for edge in trait_edges:
        target_bound = edge.g().bind(node=edge.edge().target())
        trait_name = get_type_name(target_bound)
        if trait_name:
            traits[trait_name] = traits.get(trait_name, 0) + 1

    # Recurse into children
    children: list[graph.BoundEdge] = []

    def collect_comp(ctx: list, edge: graph.BoundEdge) -> None:
        ctx.append(edge)

    fbrk.EdgeComposition.visit_children_edges(
        bound_node=bound_node, ctx=children, f=collect_comp
    )

    for edge in children:
        child_bound = edge.g().bind(node=edge.edge().target())
        child_traits = collect_trait_names(child_bound, visited)
        for k, v in child_traits.items():
            traits[k] = traits.get(k, 0) + v

    return traits


def analyze_graph(bound_node: graph.BoundNode) -> GraphMetrics:
    """Analyze a graph and return metrics."""
    metrics = GraphMetrics()

    metrics.total_nodes = count_nodes(bound_node)
    metrics.max_depth = measure_depth(bound_node)

    edge_counts = count_edges_by_type(bound_node)
    metrics.composition_edges = edge_counts.get("composition", 0)
    metrics.trait_edges = edge_counts.get("trait", 0)
    metrics.pointer_edges = edge_counts.get("pointer", 0)
    metrics.connection_edges = edge_counts.get("connection", 0)
    metrics.operand_edges = edge_counts.get("operand", 0)

    metrics.total_edges = sum(edge_counts.values())

    metrics.node_types = collect_type_names(bound_node)
    metrics.trait_types = collect_trait_names(bound_node)

    return metrics


def explore_module(module_cls: type, name: str, render: bool = True) -> GraphMetrics:
    """Explore a module and print its graph structure."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    instance = module_cls.bind_typegraph(tg=tg).create_instance(g=g)

    print(f"\n{'=' * 70}")
    print(f"Module: {name}")
    print(f"{'=' * 70}")

    metrics = analyze_graph(instance.instance)

    print(f"\nNode Statistics:")
    print(f"  Total nodes:        {metrics.total_nodes}")
    print(f"  Max depth:          {metrics.max_depth}")

    print(f"\nEdge Statistics:")
    print(f"  Total edges:        {metrics.total_edges}")
    print(f"  Composition edges:  {metrics.composition_edges}")
    print(f"  Trait edges:        {metrics.trait_edges}")
    print(f"  Pointer edges:      {metrics.pointer_edges}")
    print(f"  Connection edges:   {metrics.connection_edges}")
    print(f"  Operand edges:      {metrics.operand_edges}")

    print(f"\nNode Types (top 10):")
    sorted_types = sorted(metrics.node_types.items(), key=lambda x: -x[1])[:10]
    for type_name, count in sorted_types:
        print(f"  {type_name}: {count}")

    print(f"\nTrait Types (top 10):")
    sorted_traits = sorted(metrics.trait_types.items(), key=lambda x: -x[1])[:10]
    for trait_name, count in sorted_traits:
        print(f"  {trait_name}: {count}")

    if render:
        print(f"\nGraph Render (composition + traits + connections):")
        print("-" * 60)
        rendered = GraphRenderer.render(
            instance.instance,
            show_composition=True,
            show_traits=True,
            show_pointers=False,
            show_connections=True,
            show_operands=False,
        )
        # Limit output to prevent overwhelming console
        lines = rendered.split("\n")
        if len(lines) > 100:
            print("\n".join(lines[:100]))
            print(f"\n... ({len(lines) - 100} more lines)")
        else:
            print(rendered)

    return metrics


def print_metrics_table(results: dict[str, GraphMetrics]) -> None:
    """Print a markdown table of metrics."""
    print("\n" + "=" * 100)
    print("SUMMARY TABLE")
    print("=" * 100)

    # Header
    headers = [
        "Module",
        "Nodes",
        "Edges",
        "Comp",
        "Trait",
        "Ptr",
        "Conn",
        "Op",
        "Depth",
    ]
    header_line = "| " + " | ".join(f"{h:>10}" for h in headers) + " |"
    separator = "|" + "|".join("-" * 12 for _ in headers) + "|"

    print(header_line)
    print(separator)

    for name, m in results.items():
        row = [
            name[:10],
            str(m.total_nodes),
            str(m.total_edges),
            str(m.composition_edges),
            str(m.trait_edges),
            str(m.pointer_edges),
            str(m.connection_edges),
            str(m.operand_edges),
            str(m.max_depth),
        ]
        print("| " + " | ".join(f"{v:>10}" for v in row) + " |")


def main():
    """Run graph exploration on common library modules."""
    import sys

    # Parse arguments
    render = "--render" in sys.argv or "-r" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    if verbose:
        logging.getLogger().setLevel(logging.INFO)

    print("Graph Structure Exploration Tool")
    print("=" * 70)
    print("Exploring graph structures of library modules to understand")
    print("node/edge distributions and composition depths.")
    print()
    print(f"Options: render={render}")

    results: dict[str, GraphMetrics] = {}

    # Explore modules in order of complexity
    modules_to_explore = [
        (F.Electrical, "Electrical"),
        (F.Resistor, "Resistor"),
        (F.Capacitor, "Capacitor"),
        (F.ElectricPower, "ElectricPower"),
        (F.ElectricLogic, "ElectricLogic"),
        (F.I2C, "I2C"),
        (F.ResistorVoltageDivider, "ResistorVoltageDivider"),
    ]

    for module_cls, name in modules_to_explore:
        try:
            metrics = explore_module(module_cls, name, render=render)
            results[name] = metrics
        except Exception as e:
            print(f"\nError exploring {name}: {e}")
            import traceback

            traceback.print_exc()

    # Print summary table
    print_metrics_table(results)


if __name__ == "__main__":
    main()
