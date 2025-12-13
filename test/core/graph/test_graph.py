import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.library._F as F


def _get_component_node_count_params():
    """
    Generate test parameters lazily to avoid circular imports.
    Returns list of pytest.param(component_class, expected_count, id=name).
    """
    # Component class -> expected unique node count
    # (each node counted once, even if reachable via multiple paths)
    component_counts: dict[type, int | None] = {
        F.Electrical: 2,
        F.ElectricLogic: 206,
        F.ElectricSignal: 197,
        F.ElectricPower: 157,
        F.Resistor: 635,
        F.Capacitor: 471,
        F.I2C: 672,
    }

    return [
        pytest.param(cls, count, id=cls.__name__)
        for cls, count in component_counts.items()
    ]


@pytest.mark.parametrize(
    "component_type,expected_count",
    _get_component_node_count_params(),
)
def test_component_instance_count(component_type: type, expected_count: int | None):
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    _ = component_type.bind_typegraph(tg).create_instance(g)
    count = g.get_node_count()
    print(f"{component_type.__name__} node count: {count}")

    if expected_count is not None:
        assert count == expected_count, (
            f"{component_type.__name__} node count mismatch: "
            f"expected {expected_count}, got {count}"
        )
