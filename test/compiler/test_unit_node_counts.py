"""
Baseline test for unit-related node counts.

Builds a small ato program with multiple literals sharing the same unit
and counts unit-related nodes via tg.get_type_instance_overview().
"""

import time

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from test.compiler.conftest import build_instance

UNIT_RELATED_TYPES = {
    "is_unit",
    "is_unit_type",
    "has_unit",
    "has_display_unit",
    "_BasisVector",
    "Counts",
    "is_unit_expression",
    "UnitExpression",
    "is_si_unit",
    "is_si_prefixed_unit",
    "is_binary_prefixed_unit",
    "is_base_unit",
    "Ohm",
    "Volt",
    "Ampere",
    "Hertz",
    "Farad",
    "Henry",
    "Watt",
    "Second",
    "Meter",
    "Kelvin",
    "Mole",
    "Candela",
    "Radian",
    "Steradian",
    "Newton",
    "Pascal",
    "Joule",
    "Coulomb",
    "Siemens",
    "Weber",
    "Tesla",
    "DegreeCelsius",
    "Lumen",
    "Lux",
    "Becquerel",
    "Gray",
    "Sievert",
    "Katal",
    "Gram",
    "Bit",
    "Byte",
    "Percent",
    "Ppm",
    "Degree",
    "ArcMinute",
    "ArcSecond",
    "Minute",
    "Hour",
    "Day",
    "Week",
    "Month",
    "Year",
    "Liter",
    "Rpm",
    "AmpereHour",
    "Dimensionless",
    "_AnonymousUnit",
}


def _build_and_measure(source: str, n_params: int, param_prefix: str = "v"):
    """Build source, count nodes, and time serialization of all parameters."""
    g, tg, stdlib, result, app_root = build_instance(source, root="App")

    # Count nodes
    overview = tg.get_type_instance_overview()
    total = 0
    unit_related = 0
    counts: dict[str, int] = {}
    for type_name, count in overview:
        total += count
        counts[type_name] = counts.get(type_name, 0) + count
        base = type_name.split("<")[0]
        if base in UNIT_RELATED_TYPES:
            unit_related += count

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

    return total, unit_related, counts, elapsed_ms


def _print_table(rows: list[tuple[int, int, int, int, int, int, int, float]]) -> None:
    header = (
        f"{'lits':>5} {'total':>7} {'unit':>7}"
        f" {'is_unit':>8} {'has_unit':>9} {'has_disp':>9}"
        f" {'is_unit_type':>13} {'ser_ms':>8}"
    )
    sep = "-" * len(header)
    print(f"\n{header}")
    print(sep)
    for n_lit, total, unit_rel, is_u, has_u, has_d, is_ut, ser in rows:
        print(
            f"{n_lit:>5} {total:>7} {unit_rel:>7}"
            f" {is_u:>8} {has_u:>9} {has_d:>9}"
            f" {is_ut:>13} {ser:>8.1f}"
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

    total, unit_rel, counts, ser_ms = _build_and_measure(source, 3, "v")
    row = (
        6,
        total,
        unit_rel,
        counts.get("is_unit", 0),
        counts.get("has_unit", 0),
        counts.get("has_display_unit", 0),
        counts.get("is_unit_type", 0),
        ser_ms,
    )
    _print_table([row])

    assert total > 0, "Expected some total nodes"
    assert counts.get("has_unit", 0) > 0, "Expected some has_unit nodes"


def test_unit_node_counts_many_same_unit():
    """
    Build a program with 10 Volt literals.  Shows scaling with singleton units.
    """
    total, unit_rel, counts, ser_ms = _build_and_measure(_make_volt_source(10), 10)
    row = (
        10,
        total,
        unit_rel,
        counts.get("is_unit", 0),
        counts.get("has_unit", 0),
        counts.get("has_display_unit", 0),
        counts.get("is_unit_type", 0),
        ser_ms,
    )
    _print_table([row])


def test_unit_type_sharing():
    """
    Build programs with varying Volt literal counts via the compiler.
    Verify that unit-related instance counts grow sublinearly
    (all point to the shared type-level is_unit singleton).
    """
    rows = []
    all_counts = {}
    for n in (5, 10, 15, 20, 50, 100, 1000):
        total, unit_rel, counts, ser_ms = _build_and_measure(_make_volt_source(n), n)
        rows.append(
            (
                n,
                total,
                unit_rel,
                counts.get("is_unit", 0),
                counts.get("has_unit", 0),
                counts.get("has_display_unit", 0),
                counts.get("is_unit_type", 0),
                ser_ms,
            )
        )
        all_counts[n] = counts

    _print_table(rows)

    # is_unit instances should NOT scale with literal count (type-level singletons)
    is_unit_counts = {n: c.get("is_unit", 0) for n, c in all_counts.items()}
    assert len(set(is_unit_counts.values())) == 1, (
        f"is_unit should be constant across literal counts: {is_unit_counts}"
    )
