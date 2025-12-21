# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import csv
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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


def make_bom(components: Iterable[fabll.Module], jlcpcb_format: bool = True):
    bomlines = [line for c in components if (line := _get_bomline(c, jlcpcb_format))]
    bomlines = sorted(
        _compact_bomlines(bomlines),
        key=lambda x: split_designator(x.Designator.split(", ")[0]),
    )

    rows = [line.to_dict() for line in bomlines]
    return rows


def write_bom(
    components: Iterable[fabll.Node], path: Path, jlcpcb_format: bool = True
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


def _get_bomline(cmp: fabll.Node, jlcpcb_format: bool = True) -> BOMLine | None:
    if not (
        footprint_trait := cmp.try_get_trait(F.Footprints.has_associated_footprint)
    ):
        logger.warning(f"Missing associated footprint on component '{cmp}'")
        return None
    if cmp.has_trait(F.has_part_picked) and cmp.has_trait(F.has_part_removed):
        logger.warning(f"Component '{cmp}' has part picked and removed")
        return None

    if missing := [
        t.__name__
        for t in (
            F.has_part_picked,
            F.has_designator,
        )
        if not cmp.has_trait(t)
    ]:
        logger.warning(f"Missing fields on component '{cmp}': {missing}")
        return None

    part = cmp.get_trait(F.has_part_picked).get_part()

    kicad_footprint_trait = footprint_trait.get_footprint().try_get_trait(
        F.KiCadFootprints.has_associated_kicad_pcb_footprint
    )
    if kicad_footprint_trait is None:
        kicad_library_footprint_trait = footprint_trait.get_footprint().try_get_trait(
            F.KiCadFootprints.has_associated_kicad_library_footprint
        )
        if kicad_library_footprint_trait is None:
            logger.warning(f"Missing any form of kicad footprint on component '{cmp}'")
            return None
        footprint_name = kicad_library_footprint_trait.library_name
    else:
        footprint_name = kicad_footprint_trait.get_footprint().name

    value = (
        cmp.get_trait(F.has_simple_value_representation).get_value()
        if cmp.has_trait(F.has_simple_value_representation)
        else ""
    )
    designator = cmp.get_trait(F.has_designator).get_designator() or ""

    if jlcpcb_format and not part.supplier_partno.lower().startswith("c"):
        logger.warning(f"Non-LCSC parts not supported in JLCPCB BOM: {part}")
        return None

    manufacturer = part.manufacturer
    partnumber = part.partno

    return BOMLine(
        Designator=designator,
        Footprint=footprint_name,
        Quantity=1,
        Value=value,
        Manufacturer=manufacturer,
        Partnumber=partnumber,
        Supplier_Partnumber=part.supplier_partno,
    )


def test_get_bomline():
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
    from faebryk.libs.kicad.fileformats import kicad
    from faebryk.libs.test.fileformats import PCBFILE

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE).kicad_pcb
    k_pcb_fp = pcb.footprints[1]

    class TestFootprint(fabll.Node):
        is_footprint_ = fabll.Traits.MakeEdge(F.Footprints.is_footprint.MakeChild())
        pass

    class TestNode(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _has_designator = fabll.Traits.MakeEdge(F.has_designator.MakeChild("R1"))
        _has_part_picked = fabll.Traits.MakeEdge(
            F.has_part_picked.MakeChild(
                manufacturer="Amazing manufacturer",
                partno="ABC-Part",
                supplier_partno="C12345",
                supplier_id="lcsc",
            )
        )
        has_associated_footprint_ = fabll.Traits.MakeEdge(
            F.Footprints.has_associated_footprint.MakeChild()
        )

    node = TestNode.bind_typegraph(tg).create_instance(g=g)
    fp_node = TestFootprint.bind_typegraph(tg).create_instance(g=g)
    node.has_associated_footprint_.get().setup(fp_node.is_footprint_.get())

    transformer = PCB_Transformer(pcb, node)

    fabll.Traits.create_and_add_instance_to(
        node=node.has_associated_footprint_.get().get_footprint(),
        trait=F.KiCadFootprints.has_associated_kicad_pcb_footprint,
    ).setup(k_pcb_fp, transformer)

    bomline = _get_bomline(node)

    assert bomline is not None
    assert bomline.Designator == "R1"
    assert bomline.Footprint == "lcsc:LED0603-RD-YELLOW"
    assert bomline.Value == ""
    assert bomline.Manufacturer == "Amazing manufacturer"
    assert bomline.Partnumber == "ABC-Part"
