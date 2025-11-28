import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.library._F as F


def test_resistor_instance_visualization():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    component_instance = F.ElectricPower.bind_typegraph(tg).create_instance(g)

    print("=== Instance Graph ===")
    output = graph.TypeGraphFunctions.render(component_instance.instance)
    print(output)


def _get_component_node_count_params():
    """
    Generate test parameters lazily to avoid circular imports.
    Returns list of pytest.param(component_class, expected_count, id=name).
    """

    # Component class -> expected node count (None = don't assert, just print)
    component_counts: dict[type, int | None] = {
        F.Electrical: 2,
        F.ElectricLogic: 76,
        F.ElectricSignal: 67,
        F.ElectricPower: 29,
        F.Resistor: 429,
        F.Capacitor: 325,
        F.I2C: 212,
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
    count = graph.InstanceGraphFunctions.count_nodes(component_instance.instance)
    print(f"{component_type.__name__} node count: {count}")

    if expected_count is not None:
        assert count == expected_count, (
            f"{component_type.__name__} node count mismatch: "
            f"expected {expected_count}, got {count}"
        )
