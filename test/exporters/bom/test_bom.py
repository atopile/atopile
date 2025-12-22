# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.exporters.bom.jlcpcb import _get_bomline
from faebryk.libs.app.designators import (
    attach_random_designators,
    load_kicad_pcb_designators,
)
from faebryk.libs.picker.picker import pick_part_recursively

g = graph.GraphView.create()
tg = fbrk.TypeGraph.create(g=g)


def _build(app: fabll.Node):
    load_kicad_pcb_designators(app.tg, attach=True)
    solver = DefaultSolver()
    pick_part_recursively(app, solver)
    attach_random_designators(app.tg)


@pytest.mark.usefixtures("setup_project_config")
def test_bom_picker_pick():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    r = F.Resistor.bind_typegraph(tg).create_instance(g=g)
    r1_value = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_center_rel(
            center=10 * 1e3,
            rel=0.01,
            unit=F.Units.Ohm.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get(),
        )
    )
    r.resistance.get().alias_to_literal(g=g, value=r1_value)

    _build(r)

    bomline = _get_bomline(r)
    assert bomline is not None


@pytest.mark.usefixtures("setup_project_config")
def test_bom_explicit_pick():
    class TestComponent(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

        _is_pickable_by_supplier_id = fabll.Traits.MakeEdge(
            F.is_pickable_by_supplier_id.MakeChild(
                supplier_part_id="C25804",
                supplier=F.is_pickable_by_supplier_id.Supplier.LCSC,
            )
        )
        can_attach_to_footprint_ = fabll.Traits.MakeEdge(
            F.Footprints.can_attach_to_footprint.MakeChild()
        )
        has_designator_ = fabll.Traits.MakeEdge(F.has_designator.MakeChild("MOD"))

    test_component = TestComponent.bind_typegraph(tg).create_instance(g=g)
    _build(test_component)

    bomline = _get_bomline(test_component)
    assert bomline is not None
    assert bomline.Supplier_Partnumber == "C25804"


def _setup_test_component(tg: fbrk.TypeGraph, g: graph.GraphView):
    class TestPad(fabll.Node):
        is_pad_ = fabll.Traits.MakeEdge(
            F.Footprints.is_pad.MakeChild(pad_name="", pad_number="")
        )

    class TestFootprint(fabll.Node):
        is_footprint_ = fabll.Traits.MakeEdge(F.Footprints.is_footprint.MakeChild())

        pads_ = [TestPad.MakeChild() for _ in range(2)]

    class TestModule(fabll.Node):
        is_module_ = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        can_attach_to_footprint_ = fabll.Traits.MakeEdge(
            F.Footprints.can_attach_to_footprint.MakeChild()
        )
        has_designator_ = fabll.Traits.MakeEdge(F.has_designator.MakeChild("MOD"))

    test_module = TestModule.bind_typegraph(tg).create_instance(g=g)
    test_footprint = TestFootprint.bind_typegraph_from_instance(
        instance=test_module.instance
    ).create_instance(g=g)

    fabll.Traits.create_and_add_instance_to(
        node=test_module, trait=F.Footprints.has_associated_footprint
    ).setup(test_footprint.is_footprint_.get())

    return test_module


def test_bom_kicad_footprint_no_lcsc():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    test_module = _setup_test_component(tg, g)

    _build(test_module)

    bomline = _get_bomline(test_module)
    assert bomline is None


@pytest.mark.usefixtures("setup_project_config")
def test_bom_kicad_footprint_lcsc_verbose():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    test_module = F.Resistor.bind_typegraph(tg).create_instance(g=g)

    fabll.Traits.create_and_add_instance_to(
        node=test_module, trait=F.is_pickable_by_supplier_id
    ).setup(
        supplier_part_id="C23162",
        supplier=F.is_pickable_by_supplier_id.Supplier.LCSC,
    )
    _build(test_module)

    bomline = _get_bomline(test_module)
    assert bomline is not None
    assert bomline.Supplier_Partnumber == "C23162"
    assert bomline.Footprint == "UNI_ROYAL_0603WAF4701T5E"
    assert bomline.Manufacturer == "UNI-ROYAL(Uniroyal Elec)"
    assert bomline.Partnumber == "0603WAF4701T5E"
    # assert bomline.Value == "4.7kΩ ± 1%" #TODO
    assert bomline.Designator == "R1"
