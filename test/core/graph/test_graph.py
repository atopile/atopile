import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.library._F as F


def test_instance_visualization(capsys):
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    component_instance = F.ElectricPower.bind_typegraph(tg).create_instance(g)

    with capsys.disabled():
        print("=== Instance Graph ===")
        output = graph.InstanceGraphFunctions.render(
            component_instance.instance, show_traits=True
        )
        print(output)


def test_count_instance(capsys):
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    instance = F.OpAmp.bind_typegraph(tg).create_instance(g)

    with capsys.disabled():
        print("=== Instance Graph ===")
        output = graph.InstanceGraphFunctions.render(
            instance.instance,
            show_traits=True,
            filter_types=[
                # 'is_lead',
                # 'Electrical',
            ],
        )
        print(output)


def _get_component_node_count_params():
    """
    Generate test parameters lazily to avoid circular imports.
    Returns list of pytest.param(component_class, expected_count, id=name).
    """

    # Component class -> expected unique node count
    # (each node counted once, even if reachable via multiple paths)
    component_counts: dict[type, int | None] = {
        F.Electrical: 2,
        F.ElectricLogic: 204,
        F.ElectricSignal: 195,
        F.ElectricPower: 155,
        F.Resistor: 339,  # +2 for is_lead traits on each electrical
        F.Capacitor: 265,
        F.I2C: 668,
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
