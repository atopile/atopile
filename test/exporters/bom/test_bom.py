# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.exporters.bom.jlcpcb import _get_bomline
from faebryk.libs.app.designators import attach_random_designators, load_designators
from faebryk.libs.app.pcb import create_footprint_library
from faebryk.libs.iso_metric_screw_thread import Iso262_MetricScrewThreadSizes
from faebryk.libs.library import L
from faebryk.libs.picker.picker import pick_part_recursively
from faebryk.libs.units import P


def _build(app: Module):
    load_designators(app.get_graph(), attach=True)
    solver = DefaultSolver()
    pick_part_recursively(app, solver)
    F.has_package.standardize_footprints(app, solver)
    create_footprint_library(app, no_fp_lib=True)
    attach_random_designators(app.get_graph())


def test_bom_mounting_hole():
    mh = F.Mounting_Hole(
        diameter=Iso262_MetricScrewThreadSizes.M10,
        pad_type=F.Mounting_Hole.PadType.Pad,
    )

    _build(mh)

    bomline = _get_bomline(mh)
    assert bomline is None


def test_bom_picker_pick():
    r = F.Resistor()
    r.resistance.constrain_subset(L.Range.from_center_rel(10 * P.kohm, 0.01))

    _build(r)

    bomline = _get_bomline(r)
    assert bomline is not None


def test_bom_explicit_pick():
    m = Module()
    m.add(F.can_attach_to_footprint_symmetrically())
    m.add(F.has_explicit_part.by_supplier("C25804", pinmap={}))
    _build(m)

    bomline = _get_bomline(m)
    assert bomline is not None
    assert bomline.LCSC_Partnumber == "C25804"


def test_bom_kicad_footprint_no_lcsc():
    m = Module()
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
    m = Module()
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
    m = Module()
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
