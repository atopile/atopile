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
        _has_electric_reference = fabll.Traits.MakeEdge(
            F.has_explicit_part.setup_by_supplier("C25804")
        )
        _can_attach_to_footprint = fabll.Traits.MakeEdge(
            F.Footprints.can_attach_to_footprint.MakeChild()
        )

    test_component = TestComponent.bind_typegraph(tg).create_instance(g=g)
    _build(test_component)

    bomline = _get_bomline(test_component)
    assert bomline is not None
    assert bomline.LCSC_Partnumber == "C25804"


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

    test_module = TestModule.bind_typegraph(tg).create_instance(g=g)
    test_footprint = TestFootprint.bind_typegraph_from_instance(
        instance=test_module.instance
    ).create_instance(g=g)

    fabll.Traits.create_and_add_instance_to(
        node=test_module, trait=F.Footprints.has_associated_footprint
    ).set_footprint(test_footprint.is_footprint_.get())

    return test_module


def test_bom_kicad_footprint_no_lcsc():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    test_module = _setup_test_component(tg, g)

    _build(test_module)

    bomline = _get_bomline(test_module)
    assert bomline is None


def test_bom_kicad_footprint_lcsc_verbose():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    test_module = _setup_test_component(tg, g)

    _build(test_module)

    fabll.Traits.create_and_add_instance_to(
        node=test_module, trait=F.has_explicit_part
    ).setup_by_supplier("C18166021", pinmap={})

    _build(test_module)

    bomline = _get_bomline(test_module)
    assert bomline is not None
    assert bomline.LCSC_Partnumber == "C18166021"


def test_bom_kicad_footprint_lcsc_compact():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestModule(fabll.Node):
        is_module_ = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        can_attach_to_footprint_ = fabll.Traits.MakeEdge(
            F.Footprints.can_attach_to_footprint.MakeChild()
        )
        unnamed_ = [F.Electrical.MakeChild() for _ in range(2)]

        for e in unnamed_:
            lead = fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [e])
            lead.add_dependant(
                fabll.Traits.MakeEdge(F.Lead.can_attach_to_any_pad.MakeChild(), [lead])
            )
            e.add_dependant(lead)

    m = TestModule.bind_typegraph(tg=tg).create_instance(g=g)
    fp = F.Footprints.GenericFootprint.bind_typegraph_from_instance(
        instance=m.instance
    ).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(
        node=m, trait=F.Footprints.has_associated_footprint
    ).set_footprint(fp.is_footprint.get())

    fabll.Traits.create_and_add_instance_to(
        node=m, trait=F.has_explicit_part
    ).setup_by_supplier(
        supplier_partno="C18166021",
        pinmap={},
        override_footprint=(
            fp.is_footprint,
            "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        ),
    )

    _build(m)

    bomline = _get_bomline(m)
    assert bomline is not None
    assert bomline.LCSC_Partnumber == "C18166021"
    assert (
        m.get_trait(F.Footprints.has_associated_footprint)
        .get_footprint()
        .get_trait(F.KiCadFootprints.has_associated_kicad_pcb_footprint)
        .get_kicad_footprint_name()
        == "PinHeader_1x02_P2.54mm_Vertical"
    )
