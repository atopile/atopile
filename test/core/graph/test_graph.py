import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import indented_container


def _get_component_node_count_params():
    """
    Generate test parameters lazily to avoid circular imports.
    Returns list of pytest.param(component_class, expected_count, id=name).
    """
    # Component class -> expected unique node count
    # (each node counted once, even if reachable via multiple paths)
    component_counts: dict[type, int | None] = {
        fabll.Node: 1,
        F.Electrical: 5,
        F.ElectricLogic: 391,
        F.ElectricSignal: 382,
        F.ElectricPower: 336,
        F.Resistor: 800,
        F.Capacitor: 714,
        F.I2C: 1106,
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

    component_instance = component_type.bind_typegraph(tg).create_instance(g)
    count = len(
        component_instance.get_children(
            direct_only=False, types=fabll.Node, include_root=True
        )
    )

    print(f"{component_type.__name__} node count: {count}")
    print(indented_container(tg.get_type_instance_overview()))

    if expected_count is not None:
        assert count == expected_count, (
            f"{component_type.__name__} node count mismatch: "
            f"expected {expected_count}, got {count}"
        )
