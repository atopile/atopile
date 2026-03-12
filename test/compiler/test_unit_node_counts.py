"""
Baseline test for unit-related node counts.

Builds a small ato program with multiple literals sharing the same unit
and counts unit-related nodes by recursively walking composition children
of is_unit, has_unit, has_display_unit, and unit type nodes.
"""

import time

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.library.Units import has_display_unit, has_unit, is_unit
from test.compiler.conftest import build_instance


def _count_recursive_children(bound_node: graph.BoundNode) -> int:
    """Count a node plus all its recursive composition children."""
    count = 1  # the node itself
    children: list[graph.BoundEdge] = []

    def collect(ctx: list[graph.BoundEdge], edge: graph.BoundEdge) -> None:
        ctx.append(edge)

    fbrk.EdgeComposition.visit_children_edges(
        bound_node=bound_node, ctx=children, f=collect
    )
    for edge in children:
        count += 1  # direct child
        # recurse into grandchildren
        child_node = edge.g().bind(node=edge.edge().target())
        count += _count_recursive_children(child_node) - 1  # -1: already counted child
    return count


def _count_unit_nodes(g: graph.GraphView, tg: fbrk.TypeGraph) -> dict[str, int]:
    """
    Count unit-related nodes by walking composition children of:
    - is_unit instances (the singleton unit definitions)
    - has_unit instances (per-literal trait pointing to is_unit)
    - has_display_unit instances (per-literal trait pointing to display unit)
    - unit type nodes (Volt, Ohm, etc. — the parent types)
    """
    seen: set[int] = set()  # node UUIDs to avoid double-counting
    category_counts: dict[str, int] = {}

    def _walk_instances(label: str, instances: list) -> None:
        total = 0
        for inst in instances:
            node = inst.instance.node() if hasattr(inst, "instance") else inst.node()
            uuid = node.get_uuid()
            if uuid not in seen:
                seen.add(uuid)
                n = _count_recursive_children(
                    inst.instance if hasattr(inst, "instance") else inst
                )
                total += n
                # Mark all children as seen too
                children: list[graph.BoundEdge] = []

                def collect(ctx: list, edge: graph.BoundEdge) -> None:
                    ctx.append(edge)

                fbrk.EdgeComposition.visit_children_edges(
                    bound_node=(inst.instance if hasattr(inst, "instance") else inst),
                    ctx=children,
                    f=collect,
                )
                for edge in children:
                    seen.add(edge.edge().target().get_uuid())
        category_counts[label] = total

    # is_unit singletons (type-level, should be constant)
    is_unit_instances = list(
        fabll.Traits.get_implementors(is_unit.bind_typegraph(tg), g)
    )
    _walk_instances("is_unit", is_unit_instances)

    # has_unit instances (per-literal)
    has_unit_instances = list(
        fabll.Traits.get_implementors(has_unit.bind_typegraph(tg), g)
    )
    _walk_instances("has_unit", has_unit_instances)

    # has_display_unit instances (per-literal)
    has_disp_instances = list(
        fabll.Traits.get_implementors(has_display_unit.bind_typegraph(tg), g)
    )
    _walk_instances("has_display_unit", has_disp_instances)

    category_counts["total_seen"] = len(seen)
    category_counts["is_unit_count"] = len(is_unit_instances)
    category_counts["has_unit_count"] = len(has_unit_instances)
    category_counts["has_display_unit_count"] = len(has_disp_instances)

    return category_counts


def _build_and_measure(source: str, n_params: int, param_prefix: str = "v"):
    """Build source, count nodes, and time serialization of all parameters."""
    g, tg, stdlib, result, app_root = build_instance(source, root="App")

    # Total node count from overview
    overview = tg.get_type_instance_overview()
    total = sum(count for _, count in overview)

    # Unit node counts via recursive traversal
    unit_counts = _count_unit_nodes(g, tg)

    # Collect parameters
    params = []
    for i in range(1, n_params + 1):
        child = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=fabll.Node(app_root).instance,
            child_identifier=f"{param_prefix}{i}",
        )
        if child is not None:
            params.append(F.Parameters.NumericParameter.bind_instance(child))

    # Time serialization: get_values() on every parameter
    t0 = time.perf_counter()
    for p in params:
        p.get_values()
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return total, unit_counts, elapsed_ms


def _print_table(
    rows: list[tuple[int, int, int, int, int, int, int, float]],
) -> None:
    header = (
        f"{'lits':>5} {'total':>7} {'u_nodes':>8}"
        f" {'is_unit':>8} {'has_unit':>9} {'has_disp':>9}"
        f" {'ser_ms':>8}"
    )
    sep = "-" * len(header)
    print(f"\n{header}")
    print(sep)
    for n_lit, total, u_nodes, is_u, has_u, has_d, ser in rows:
        print(
            f"{n_lit:>5} {total:>7} {u_nodes:>8}"
            f" {is_u:>8} {has_u:>9} {has_d:>9}"
            f" {ser:>8.1f}"
        )


def _make_volt_source(n: int) -> str:
    lines = [f"        v{i} = {i}V" for i in range(1, n + 1)]
    return "    module App:\n" + "\n".join(lines) + "\n"


def test_unit_node_counts_basic():
    """
    Build a simple program with mixed Volt/Ohm literals and count unit-related nodes.
    """
    source = """\
    module App:
        v1 = 5V
        v2 = 10V
        v3 = 3.3V
        r1 = 10kohm
        r2 = 4.7kohm
        r3 = 100ohm
    """

    total, uc, ser_ms = _build_and_measure(source, 3, "v")
    row = (
        6,
        total,
        uc["total_seen"],
        uc["is_unit_count"],
        uc["has_unit_count"],
        uc["has_display_unit_count"],
        ser_ms,
    )
    _print_table([row])

    assert total > 0, "Expected some total nodes"
    assert uc["has_unit_count"] > 0, "Expected some has_unit nodes"


def test_unit_node_counts_many_same_unit():
    """
    Build a program with 10 Volt literals.  Shows scaling with singleton units.
    """
    total, uc, ser_ms = _build_and_measure(_make_volt_source(10), 10)
    row = (
        10,
        total,
        uc["total_seen"],
        uc["is_unit_count"],
        uc["has_unit_count"],
        uc["has_display_unit_count"],
        ser_ms,
    )
    _print_table([row])


def test_unit_type_sharing():
    """
    Build programs with varying Volt literal counts via the compiler.
    Verify that is_unit instance counts stay constant
    (all point to the shared type-level is_unit singleton).
    """
    rows = []
    all_uc = {}
    for n in (5, 10, 15, 20, 50, 100, 1000):
        total, uc, ser_ms = _build_and_measure(_make_volt_source(n), n)
        rows.append(
            (
                n,
                total,
                uc["total_seen"],
                uc["is_unit_count"],
                uc["has_unit_count"],
                uc["has_display_unit_count"],
                ser_ms,
            )
        )
        all_uc[n] = uc

    _print_table(rows)

    # is_unit instances should NOT scale with literal count (type-level singletons)
    is_unit_counts = {n: c["is_unit_count"] for n, c in all_uc.items()}
    assert len(set(is_unit_counts.values())) == 1, (
        f"is_unit should be constant across literal counts: {is_unit_counts}"
    )
