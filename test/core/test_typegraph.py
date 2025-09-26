from __future__ import annotations

from faebryk.core.type import (
    Class_ChildReference,
    Class_ImplementsType,
    Class_MakeChild,
    Type_ImplementsTrait,
    Type_ImplementsType,
    _Node,
    get_child_by_name,
    get_type_by_name,
    instantiate,
    make_child_rule_and_child_ref,
)


def test_bootstrap_types_are_registered() -> None:
    assert get_type_by_name("ImplementsType") is Type_ImplementsType
    assert get_type_by_name("ImplementsTrait") is Type_ImplementsTrait

    assert isinstance(Type_ImplementsType, Class_ImplementsType.Proto_Type)
    assert isinstance(Type_ImplementsTrait, Class_ImplementsType.Proto_Type)

    assert (get_child_by_name(Type_ImplementsType, "ImplementsType")) is not None
    assert (get_child_by_name(Type_ImplementsType, "ImplementsTrait")) is not None

    assert (get_child_by_name(Type_ImplementsTrait, "ImplementsType")) is not None
    assert (get_child_by_name(Type_ImplementsTrait, "ImplementsTrait")) is not None


def test_type_generation() -> None:
    Type_Test = Class_ImplementsType.init_type_node(_Node(), "Test")

    assert isinstance(Type_Test, Class_ImplementsType.Proto_Type)
    assert (get_child_by_name(Type_ImplementsType, "ImplementsType")) is not None
    assert (get_child_by_name(Type_ImplementsType, "ImplementsTrait")) is not None


def test_resistor_type_generation() -> None:
    from faebryk.library._F import Resistor

    Type_Resistor = get_type_by_name("Resistor")

    assert isinstance(Type_Resistor, Class_ImplementsType.Proto_Type)
    print(Type_Resistor.children.get_children())
    assert (get_child_by_name(Type_Resistor, "ImplementsType")) is not None
    make_child_rule = get_child_by_name(Type_Resistor, "resistance")
    assert isinstance(make_child_rule, Class_MakeChild.Proto_MakeChild)
    child_reference = make_child_rule.child_ref_pointer.get_reference()
    assert isinstance(child_reference, Class_ChildReference.Proto_ChildReference)
    child_type_node = child_reference.node_type_pointer.get_reference()
    assert isinstance(child_type_node, Class_ImplementsType.Proto_Type)
    assert child_type_node._identifier == "Parameter"
    assert child_reference._identifier == "resistance"


def test_has_usage_example_trait_type_generation() -> None:
    from faebryk.library._F import has_usage_example

    Type_HasUsageExample = get_type_by_name("has_usage_example")

    assert isinstance(Type_HasUsageExample, Class_ImplementsType.Proto_Type)
    print(Type_HasUsageExample.children.get_children())
    assert (get_child_by_name(Type_HasUsageExample, "ImplementsType")) is not None
    assert (get_child_by_name(Type_HasUsageExample, "ImplementsTrait")) is not None


def test_resistor_instance_generation() -> None:
    from faebryk.library._F import Resistor

    r = Resistor()
    Type_Electrical = get_type_by_name("Electrical")

    # Lift of Electrical Children
    unnamed0 = get_child_by_name(r.instance_node, "unnamed[0]")
    assert isinstance(unnamed0, _Node.Proto_Node)
    assert unnamed0.is_type.get_children() == [Type_Electrical]


def test_standard_library_typegraph() -> None:
    import faebryk.library._F as F

    assert get_type_by_name("has_usage_example") is not None
    assert get_type_by_name("has_designator_prefix") is not None
    assert get_type_by_name("is_pickable") is not None
    assert get_type_by_name("Electrical") is not None
    assert get_type_by_name("Footprint") is not None
    assert get_type_by_name("is_pickable_by_type") is not None
    assert get_type_by_name("can_attach_to_footprint") is not None
    assert get_type_by_name("can_attach_to_footprint_symmetrically") is not None
    assert get_type_by_name("Resistor") is not None


if __name__ == "__main__":
    test_has_usage_example_trait_type_generation()
