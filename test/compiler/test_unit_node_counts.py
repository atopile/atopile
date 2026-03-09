"""
Baseline test for unit-related node counts.

Builds a small ato program with multiple literals sharing the same unit
and counts unit-related nodes via tg.get_type_instance_overview().
"""

from test.compiler.conftest import build_instance

KEY_TYPES = ("is_unit", "has_unit", "has_display_unit")


def _count_nodes(source: str) -> tuple[int, dict[str, int]]:
    """Build source, return (total_nodes, {type_name: count}) for unit types."""
    g, tg, stdlib, result, app_root = build_instance(source, root="App")
    overview = tg.get_type_instance_overview()
    total = sum(count for _, count in overview)
    counts: dict[str, int] = {}
    for type_name, count in overview:
        counts[type_name] = counts.get(type_name, 0) + count
    return total, counts


def _print_table(rows: list[tuple[int, int, int, int, int]]) -> None:
    """Print a table: literals | total | is_unit | has_unit | has_display_unit."""
    header = (
        f"{'literals':>8} {'total':>8} {'is_unit':>8} {'has_unit':>9} {'has_disp':>9}"
    )
    sep = "-" * len(header)
    print(f"\n{header}")
    print(sep)
    for n_lit, total, is_u, has_u, has_d in rows:
        print(f"{n_lit:>8} {total:>8} {is_u:>8} {has_u:>9} {has_d:>9}")


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

    total, counts = _count_nodes(source)
    row = (
        6,
        total,
        counts.get("is_unit", 0),
        counts.get("has_unit", 0),
        counts.get("has_display_unit", 0),
    )
    _print_table([row])

    assert total > 0, "Expected some total nodes"
    assert counts.get("has_unit", 0) > 0, "Expected some has_unit nodes"


def test_unit_node_counts_many_same_unit():
    """
    Build a program with 10 Volt literals.  Shows scaling with singleton units.
    """
    total, counts = _count_nodes(_make_volt_source(10))
    row = (
        10,
        total,
        counts.get("is_unit", 0),
        counts.get("has_unit", 0),
        counts.get("has_display_unit", 0),
    )
    _print_table([row])


def test_unit_type_sharing():
    """
    Build programs with 5 and 10 Volt literals via the compiler.
    Verify that unit-related instance counts grow sublinearly
    (all point to the shared type-level is_unit singleton).
    """
    rows = []
    all_counts = {}
    for n in (5, 10):
        total, counts = _count_nodes(_make_volt_source(n))
        rows.append(
            (
                n,
                total,
                counts.get("is_unit", 0),
                counts.get("has_unit", 0),
                counts.get("has_display_unit", 0),
            )
        )
        all_counts[n] = counts

    _print_table(rows)

    # is_unit instances should NOT scale with literal count (type-level singletons)
    assert all_counts[10].get("is_unit", 0) == all_counts[5].get("is_unit", 0), (
        f"is_unit should not grow: 5-lit={all_counts[5].get('is_unit', 0)}, "
        f"10-lit={all_counts[10].get('is_unit', 0)}"
    )
