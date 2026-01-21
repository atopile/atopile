# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import csv
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


@dataclass
class BOMLine:
    Designator: str
    Footprint: str
    Quantity: int
    Value: str
    Manufacturer: str
    Partnumber: str
    Supplier_Partnumber: str

    def to_dict(self) -> dict[str, str]:
        out = vars(self)
        out["LCSC Part #"] = out.pop("Supplier_Partnumber")
        return out


def rename_column(rows: list[dict[str, str]], old: str, new: str) -> None:
    for row in rows:
        row[new] = row.pop(old)


def split_designator(designator: str) -> tuple[str, int]:
    match = re.compile(r"(\d+)$").search(designator)
    if match is None:
        return (designator, 0)
    prefix = designator[: match.start()]
    number = int(match.group())
    return (prefix, number)


def make_bom(
    components: Iterable[F.Pickable.has_part_picked], jlcpcb_format: bool = True
):
    bomlines = [line for c in components if (line := _get_bomline(c, jlcpcb_format))]
    bomlines = sorted(
        _compact_bomlines(bomlines),
        key=lambda x: split_designator(x.Designator.split(", ")[0]),
    )

    rows = [line.to_dict() for line in bomlines]
    return rows


def write_bom(
    components: Iterable[F.Pickable.has_part_picked],
    path: Path,
    jlcpcb_format: bool = True,
) -> None:
    if not path.parent.exists():
        os.makedirs(path.parent)
    with open(path, "w", newline="", encoding="utf-8") as bom_csv:
        rows = make_bom(components, jlcpcb_format)
        if rows:
            writer = csv.DictWriter(
                bom_csv,
                fieldnames=list(rows[0].keys()),
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)


def _compact_bomlines(bomlines: list[BOMLine]) -> list[BOMLine]:
    compact_bomlines = []
    for row, bomline in enumerate(bomlines):
        # skip PNs that we already added
        if bomline.Supplier_Partnumber in [
            row.Supplier_Partnumber for row in compact_bomlines
        ]:
            continue

        compact_bomline = bomline
        for other_bomline in bomlines[row + 1 :]:
            if bomline.Supplier_Partnumber == other_bomline.Supplier_Partnumber:
                for key in "Footprint", "Value":
                    if getattr(bomline, key) != getattr(other_bomline, key):
                        logger.warning(
                            f"{key} is not the same for two equal partnumbers "
                            f"{bomline.Supplier_Partnumber}: "
                            f"{bomline.Designator} "
                            f"with {key}: {getattr(bomline, key)} "
                            f"{other_bomline.Designator} "
                            f"with {key}: {getattr(other_bomline, key)}"
                        )
                # Sort designators in bomline by number
                compact_bomline.Designator = ", ".join(
                    sorted(
                        (
                            compact_bomline.Designator + ", " + other_bomline.Designator
                        ).split(", "),
                        key=lambda x: split_designator(x),
                    )
                )
                compact_bomline.Quantity += other_bomline.Quantity
        compact_bomlines += [compact_bomline]

    return compact_bomlines


def _get_footprint_name(part: F.Pickable.has_part_picked) -> str:
    module = part.get_sibling_trait(fabll.is_module)
    module_locator = module.get_module_locator()
    if not (
        footprint_trait := part.try_get_sibling_trait(
            F.Footprints.has_associated_footprint
        )
    ):
        logger.warning(
            f"No footprint for '{module_locator}' will result in empty footprint column"
            " in bom"
        )
        return ""

    if kicad_footprint_trait := footprint_trait.get_footprint().try_get_trait(
        F.KiCadFootprints.has_associated_kicad_pcb_footprint
    ):
        return kicad_footprint_trait.get_footprint().name
    elif kicad_library_footprint_trait := footprint_trait.get_footprint().try_get_trait(
        F.KiCadFootprints.has_associated_kicad_library_footprint
    ):
        return kicad_library_footprint_trait.get_library_name()

    logger.warning(
        f"Missing any form of kicad footprint on component '{module_locator}'"
    )
    return ""


def _get_bomline(
    part: F.Pickable.has_part_picked, jlcpcb_format: bool = True
) -> BOMLine | None:
    module_name = part.get_sibling_trait(fabll.is_module).get_module_locator()
    if not (designator_t := part.try_get_sibling_trait(F.has_designator)):
        raise ValueError(f"Part '{part}' without designator")
    designator = designator_t.get_designator() or ""

    if hsvp := part.try_get_sibling_trait(F.has_simple_value_representation):
        value = hsvp.get_value()
    else:
        value = ""

    footprint_name = _get_footprint_name(part)
    picked_part = part.get_part()

    if jlcpcb_format and not picked_part.supplier_partno.lower().startswith("c"):
        logger.warning(f"Non-LCSC parts not supported in JLCPCB BOM: {module_name}")
        return None

    manufacturer = picked_part.manufacturer
    partnumber = picked_part.partno
    supplier_partnumber = picked_part.supplier_partno

    out = BOMLine(
        Designator=designator,
        Footprint=footprint_name,
        Quantity=1,
        Value=value,
        Manufacturer=manufacturer,
        Partnumber=partnumber,
        Supplier_Partnumber=supplier_partnumber,
    )

    logger.info(f"BOMLine for {module_name} {out=}")

    return out


# TODO: move to global fixtures
@pytest.fixture()
def setup_project_config(tmp_path):
    from atopile.config import ProjectConfig, ProjectPaths, config

    config.project = ProjectConfig.skeleton(
        entry="", paths=ProjectPaths(build=tmp_path / "build", root=tmp_path)
    )
    yield


class TestJLCBom:
    @staticmethod
    def test_get_bomline():
        from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
        from faebryk.libs.kicad.fileformats import kicad
        from faebryk.libs.test.fileformats import PCBFILE

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE).kicad_pcb
        k_pcb_fp = pcb.footprints[1]

        class _TestFootprint(fabll.Node):
            is_footprint_ = fabll.Traits.MakeEdge(F.Footprints.is_footprint.MakeChild())
            pass

        class _TestNode(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            _has_designator = fabll.Traits.MakeEdge(F.has_designator.MakeChild("R1"))
            _has_part_picked = fabll.Traits.MakeEdge(
                F.Pickable.has_part_picked.MakeChild(
                    manufacturer="Amazing manufacturer",
                    partno="ABC-Part",
                    supplier_partno="C12345",
                    supplier_id="lcsc",
                )
            )
            has_associated_footprint_ = fabll.Traits.MakeEdge(
                F.Footprints.has_associated_footprint.MakeChild()
            )

        node = _TestNode.bind_typegraph(tg).create_instance(g=g)
        fp_node = _TestFootprint.bind_typegraph(tg).create_instance(g=g)
        node.has_associated_footprint_.get().setup(fp_node.is_footprint_.get())

        transformer = PCB_Transformer(pcb, node)

        fabll.Traits.create_and_add_instance_to(
            node=node.has_associated_footprint_.get().get_footprint(),
            trait=F.KiCadFootprints.has_associated_kicad_pcb_footprint,
        ).setup(k_pcb_fp, transformer)

        bomline = _get_bomline(node.get_trait(F.Pickable.has_part_picked))

        assert bomline is not None
        assert bomline.Designator == "R1"
        assert bomline.Footprint == "lcsc:LED0603-RD-YELLOW"
        assert bomline.Value == ""
        assert bomline.Manufacturer == "Amazing manufacturer"
        assert bomline.Partnumber == "ABC-Part"

    @staticmethod
    def _test_build(app: fabll.Node):
        from faebryk.core.solver.solver import Solver
        from faebryk.libs.app.designators import (
            attach_random_designators,
            load_kicad_pcb_designators,
        )
        from faebryk.libs.picker.picker import pick_parts_recursively

        load_kicad_pcb_designators(app.tg, attach=True)
        solver = Solver()
        pick_parts_recursively(app, solver)
        attach_random_designators(app.tg)

    @pytest.mark.usefixtures("setup_project_config")
    @staticmethod
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
                unit=F.Units.Ohm.bind_typegraph(tg=tg)
                .create_instance(g=g)
                .is_unit.get(),
            )
        )
        r.resistance.get().set_superset(g=g, value=r1_value)

        TestJLCBom._test_build(r)

        bomline = _get_bomline(r.get_trait(F.Pickable.has_part_picked))
        assert bomline is not None

    @pytest.mark.usefixtures("setup_project_config")
    @staticmethod
    def test_bom_explicit_pick():
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        # Instantiate units needed for deserializing picked part attributes
        # (C25804 is a resistor with resistance, power, and voltage attributes)
        _ = F.Units.Ohm.bind_typegraph(tg).create_instance(g=g)
        _ = F.Units.Watt.bind_typegraph(tg).create_instance(g=g)
        _ = F.Units.Volt.bind_typegraph(tg).create_instance(g=g)

        class _TestComponent(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

            _is_pickable_by_supplier_id = fabll.Traits.MakeEdge(
                F.Pickable.is_pickable_by_supplier_id.MakeChild(
                    supplier_part_id="C25804",
                    supplier=F.Pickable.is_pickable_by_supplier_id.Supplier.LCSC,
                )
            )
            can_attach_to_footprint_ = fabll.Traits.MakeEdge(
                F.Footprints.can_attach_to_footprint.MakeChild()
            )
            has_designator_ = fabll.Traits.MakeEdge(F.has_designator.MakeChild("MOD"))

        test_component = _TestComponent.bind_typegraph(tg).create_instance(g=g)
        TestJLCBom._test_build(test_component)

        bomline = _get_bomline(test_component.get_trait(F.Pickable.has_part_picked))
        assert bomline is not None
        assert bomline.Supplier_Partnumber == "C25804"

    @staticmethod
    def test_bom_kicad_footprint_no_lcsc():
        from faebryk.libs.picker.lcsc import PickSupplierLCSC
        from faebryk.libs.picker.picker import PickedPart

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class _TestPad(fabll.Node):
            is_pad_ = fabll.Traits.MakeEdge(
                F.Footprints.is_pad.MakeChild(pad_name="", pad_number="")
            )

        class _TestFootprint(fabll.Node):
            is_footprint_ = fabll.Traits.MakeEdge(F.Footprints.is_footprint.MakeChild())

            pads_ = [_TestPad.MakeChild() for _ in range(2)]

        class _TestModule(fabll.Node):
            is_module_ = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            can_attach_to_footprint_ = fabll.Traits.MakeEdge(
                F.Footprints.can_attach_to_footprint.MakeChild()
            )
            has_designator_ = fabll.Traits.MakeEdge(F.has_designator.MakeChild("MOD"))

        test_module = _TestModule.bind_typegraph(tg).create_instance(g=g)
        test_footprint = _TestFootprint.bind_typegraph_from_instance(
            instance=test_module.instance
        ).create_instance(g=g)

        fabll.Traits.create_and_add_instance_to(
            node=test_module, trait=F.Footprints.has_associated_footprint
        ).setup(test_footprint.is_footprint_.get())

        fabll.Traits.create_and_add_instance_to(
            node=test_module, trait=F.Pickable.has_part_picked
        ).setup(
            PickedPart(
                manufacturer="TestManu",
                partno="TestPart",
                supplier_partno="TestSupplierPart",
                supplier=PickSupplierLCSC(),
            )
        )

        TestJLCBom._test_build(test_module)

        bomline = _get_bomline(test_module.get_trait(F.Pickable.has_part_picked))
        assert bomline is None

    @pytest.mark.usefixtures("setup_project_config")
    @staticmethod
    @pytest.mark.skip(reason="to_fix")  # FIXME
    def test_bom_kicad_footprint_lcsc_verbose():
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        test_module = F.Resistor.bind_typegraph(tg).create_instance(g=g)

        fabll.Traits.create_and_add_instance_to(
            node=test_module, trait=F.Pickable.is_pickable_by_supplier_id
        ).setup(
            supplier_part_id="C23162",
            supplier=F.Pickable.is_pickable_by_supplier_id.Supplier.LCSC,
        )
        TestJLCBom._test_build(test_module)

        bomline = _get_bomline(test_module.get_trait(F.Pickable.has_part_picked))
        assert bomline is not None
        assert bomline.Supplier_Partnumber == "C23162"
        assert bomline.Footprint == "UNI_ROYAL_0603WAF4701T5E"
        assert bomline.Manufacturer == "UNI-ROYAL(Uniroyal Elec)"
        assert bomline.Partnumber == "0603WAF4701T5E"
        assert bomline.Value == "4700±1.0%Ω 0.1W 75V"
        assert bomline.Designator == "R1"
