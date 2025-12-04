import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll


def graph_and_typegraph():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    return g, tg


def test_trait_equality():
    g, tg = graph_and_typegraph()

    class Trait1(fabll.Node):
        _is_trait = fabll.Traits.MakeEdge(
            fabll.ImplementsTrait.MakeChild().put_on_type()
        )

    class Trait2(fabll.Node):
        _is_trait = fabll.Traits.MakeEdge(
            fabll.ImplementsTrait.MakeChild().put_on_type()
        )

    trait1_a = Trait1.bind_typegraph(tg=tg).create_instance(g=g)
    trait1_b = Trait1.bind_typegraph(tg=tg).create_instance(g=g)
    trait2 = Trait2.bind_typegraph(tg=tg).create_instance(g=g)

    assert trait1_a != trait1_b
    assert trait1_a == trait1_a
    assert trait1_a.has_same_type_as(trait1_b)
    assert not trait1_a.has_same_type_as(trait2)

    trait1_type = Trait1.bind_typegraph(tg=tg).get_or_create_type()
    trait2_type = Trait2.bind_typegraph(tg=tg).get_or_create_type()
    assert trait1_type == Trait1.bind_typegraph(tg=tg).get_or_create_type()
    assert trait1_type != trait2_type


def test_trait_basic_operations():
    g, tg = graph_and_typegraph()

    class TraitWithValue(fabll.Node):
        _is_trait = fabll.Traits.MakeEdge(
            fabll.ImplementsTrait.MakeChild().put_on_type()
        )

        def __init__(self, instance: graph.BoundNode):
            super().__init__(instance=instance)
            self.value: int | None = None

        def setup(self, value: int = 1) -> "TraitWithValue":
            self.value = value
            return self

        def do(self) -> int:
            assert self.value is not None
            return self.value

    obj = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)

    assert not obj.has_trait(TraitWithValue)
    with pytest.raises(fabll.TraitNotFound):
        obj.get_trait(TraitWithValue)

    trait_instance = fabll.Traits.create_and_add_instance_to(obj, TraitWithValue).setup(
        1
    )
    assert obj.has_trait(TraitWithValue)
    assert obj.get_trait(TraitWithValue) == trait_instance
    assert trait_instance.do() == 1

    # Adding another instance of the same trait keeps the first one as the default
    replacement = fabll.Traits.create_and_add_instance_to(obj, TraitWithValue).setup(5)
    assert replacement != trait_instance
    assert obj.get_trait(TraitWithValue) == trait_instance


def test_trait_object_binding():
    g, tg = graph_and_typegraph()

    class TraitA(fabll.Node):
        _is_trait = fabll.Traits.MakeEdge(
            fabll.ImplementsTrait.MakeChild().put_on_type()
        )

    class TraitB(fabll.Node):
        _is_trait = fabll.Traits.MakeEdge(
            fabll.ImplementsTrait.MakeChild().put_on_type()
        )

    obj = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)

    unbound_trait = TraitA.bind_typegraph(tg=tg).create_instance(g=g)
    with pytest.raises(AssertionError):
        fabll.Traits(unbound_trait).get_obj_raw()

    trait_a = fabll.Traits.create_and_add_instance_to(obj, TraitA)
    trait_b = fabll.Traits.create_and_add_instance_to(obj, TraitB)

    assert fabll.Traits(trait_a).get_obj_raw() == obj
    assert trait_a.get_sibling_trait(TraitB) == trait_b


# TODO need to implement a test for multiple trait arbitration,
# test and core logic need to be updated
@pytest.mark.xfail(
    reason="TODO: need to decide deduplication strategy for multiple trait instances"
)
def test_trait_first_instance_wins():
    g, tg = graph_and_typegraph()

    class Trait(fabll.Node):
        _is_trait = fabll.Traits.MakeEdge(
            fabll.ImplementsTrait.MakeChild().put_on_type()
        )

    obj = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)

    first = fabll.Traits.create_and_add_instance_to(obj, Trait)
    second = fabll.Traits.create_and_add_instance_to(obj, Trait)

    assert first != second
    # assert obj.get_trait(Trait) == first
    assert obj.get_trait(Trait) == second

    trait_instances = Trait.bind_typegraph(tg=tg).get_instances(g=g)
    assert len(trait_instances) == 2
    assert set(trait_instances) == {first, second}
