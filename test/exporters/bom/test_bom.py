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
    load_designators(app.get_graph(), attach=True)
    solver = DefaultSolver()
    pick_part_recursively(app, solver)
    attach_random_designators(app.get_graph())


@pytest.mark.usefixtures("setup_project_config")
def test_bom_picker_pick():
    r = F.Resistor()
    r.resistance.constrain_subset(fabll.Range.from_center_rel(10 * 1e3 * F.Units.Ohm, 0.01))

    _build(r)

    bomline = _get_bomline(r)
    assert bomline is not None


@pytest.mark.usefixtures("setup_project_config")
def test_bom_explicit_pick():
    class TestComponent(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _has_electric_reference = fabll.Traits.MakeEdge(F.has_explicit_part.setup_by_supplier("C25804"))
        _can_attach_to_footprint = fabll.Traits.MakeEdge(F.can_attach_to_footprint_symmetrically.MakeChild())

    test_component = TestComponent.bind_typegraph(tg).create_instance(g=g)
    _build(test_component)

    bomline = _get_bomline(test_component)
    assert bomline is not None
    assert bomline.LCSC_Partnumber == "C25804"

def test_bom_kicad_footprint_no_lcsc():
    m = fabll.Module()
    m.add(F.can_attach_to_footprint_symmetrically())
    fp = F.KicadFootprint(pin_names=["1", "2"])
    fp.add(
        F.KicadFootprint.has_kicad_identifier(
            "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
        )
    )
    m.get_trait(F.can_attach_to_footprint).attach(fp)
    _build(m)

    bomline = _get_bomline(m)
    assert bomline is None


def test_bom_kicad_footprint_lcsc_verbose():
    m = fabll.Module()
    m.add(F.can_attach_to_footprint_symmetrically())
    fp = F.KicadFootprint(pin_names=["1", "2"])
    fp.add(
        F.KicadFootprint.has_kicad_identifier(
            "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
        )
    )
    m.get_trait(F.can_attach_to_footprint).attach(fp)
    m.add(F.has_explicit_part.by_supplier("C18166021", pinmap={}))

    _build(m)

    bomline = _get_bomline(m)
    assert bomline is not None
    assert bomline.LCSC_Partnumber == "C18166021"
    assert m.get_trait(F.has_footprint).get_footprint() is fp


def test_bom_kicad_footprint_lcsc_compact():
    m = fabll.Module()
    m.add(F.can_attach_to_footprint_symmetrically())
    m.add(
        F.has_explicit_part.by_supplier(
            "C18166021",
            pinmap={},
            override_footprint=(
                F.KicadFootprint(pin_names=["1", "2"]),
                "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
            ),
        )
    )

    _build(m)

    bomline = _get_bomline(m)
    assert bomline is not None
    assert bomline.LCSC_Partnumber == "C18166021"
    assert (
        m.get_trait(F.has_footprint)
        .get_footprint()
        .get_trait(F.has_kicad_footprint)
        .get_kicad_footprint_name()
        == "PinHeader_1x02_P2.54mm_Vertical"
    )
