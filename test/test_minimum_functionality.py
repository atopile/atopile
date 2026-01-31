import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


@pytest.mark.smoke
def test_instantiate_resistor_2():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    Resistor = F.Resistor.bind_typegraph(tg=tg)
    res_inst = Resistor.create_instance(g=g)
    assert res_inst
    assert fabll.Traits(res_inst._is_module.get()).get_obj_raw().isinstance(F.Resistor)
