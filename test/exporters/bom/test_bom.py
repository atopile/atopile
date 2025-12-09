# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.exporters.bom.jlcpcb import _get_bomline
from faebryk.libs.app.designators import attach_random_designators, load_designators
from faebryk.libs.picker.picker import pick_part_recursively

g = graph.GraphView.create()
tg = fbrk.TypeGraph.create(g=g)


def _build(app: fabll.Node):
    load_designators(app.tg, attach=True)
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


def test_bom_kicad_footprint_no_lcsc():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    m = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    fp = F.Footprints.GenericFootprint.bind_typegraph_from_instance(
        instance=m.instance
    ).create_instance(g=g)
    fp.setup([("", "2"), ("", "1")])
    fabll.Traits.create_and_add_instance_to(
        node=m, trait=F.Footprints.has_associated_footprint
    ).set_footprint(fp.is_footprint.get())
    kfp = F.KiCadFootprints.GenericKiCadFootprint.bind_typegraph_from_instance(
        instance=fp.instance
    ).create_instance(g=g)
    kfp.is_kicad_footprint_.get().setup(
        "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
    )
    fabll.Traits.create_and_add_instance_to(
        node=fp, trait=F.KiCadFootprints.has_linked_kicad_footprint
    ).setup(kfp)

    _build(m)

    bomline = _get_bomline(m)
    assert bomline is None


def test_bom_kicad_footprint_lcsc_verbose():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    m = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    fp = F.Footprints.GenericFootprint.bind_typegraph_from_instance(
        instance=m.instance
    ).create_instance(g=g)
    fp.setup([("", "2"), ("", "1")])
    fabll.Traits.create_and_add_instance_to(
        node=m, trait=F.Footprints.has_associated_footprint
    ).set_footprint(fp.is_footprint.get())
    kfp = F.KiCadFootprints.GenericKiCadFootprint.bind_typegraph_from_instance(
        instance=fp.instance
    ).create_instance(g=g)
    kfp.is_kicad_footprint_.get().setup(
        "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
    )
    fabll.Traits.create_and_add_instance_to(
        node=fp, trait=F.KiCadFootprints.has_linked_kicad_footprint
    ).setup(kfp)

    _build(m)

    fabll.Traits.create_and_add_instance_to(
        node=m, trait=F.has_explicit_part
    ).setup_by_supplier("C18166021", pinmap={})

    _build(m)

    bomline = _get_bomline(m)
    assert bomline is not None
    assert bomline.LCSC_Partnumber == "C18166021"
    assert m.get_trait(F.Footprints.has_associated_footprint).get_footprint() is fp


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
        .get_trait(F.KiCadFootprints.is_kicad_footprint)
        .get_kicad_footprint_name()
        == "PinHeader_1x02_P2.54mm_Vertical"
    )
