import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


def test_resistor_instantiation():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    Resistor = F.Resistor.bind_typegraph(tg=tg)
    res_inst = Resistor.create_instance(g=g)
    assert Resistor.get_trait(F.has_usage_example)
    assert res_inst
    assert res_inst._type_identifier() == "Resistor"
    assert res_inst.unnamed[0].get().get_name() == "unnamed[0]"
    assert res_inst.resistance.get().get_name() == "resistance"
    assert (
        fabll.Traits(res_inst.resistance.get().get_units())
        .get_obj_raw()
        .get_type_name()
        == "Ohm"
    )
    assert res_inst.get_trait(fabll.is_module)
    electricals = (
        res_inst.get_trait(F.can_attach_to_footprint_symmetrically)
        .electricals_.get()
        .as_list()
    )
    assert electricals[0].get_name() == "unnamed[0]"
    assert electricals[1].get_name() == "unnamed[1]"
    assert (
        res_inst._is_pickable.get().get_param("resistance").get_name() == "resistance"
    )
