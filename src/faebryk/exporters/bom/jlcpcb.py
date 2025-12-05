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
from faebryk.libs.picker.lcsc import PickedPartLCSC

logger = logging.getLogger(__name__)


@dataclass
class BOMLine:
    Designator: str
    Footprint: str
    Quantity: int
    Value: str
    Manufacturer: str
    Partnumber: str
    LCSC_Partnumber: str

    def to_dict(self) -> dict[str, str]:
        out = vars(self)
        out["LCSC Part #"] = out.pop("LCSC_Partnumber")
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


def make_bom(components: Iterable[fabll.Module]):
    bomlines = [line for c in components if (line := _get_bomline(c))]
    bomlines = sorted(
        _compact_bomlines(bomlines),
        key=lambda x: split_designator(x.Designator.split(", ")[0]),
    )

    rows = [line.to_dict() for line in bomlines]
    return rows


def write_bom_jlcpcb(components: Iterable[fabll.Node], path: Path) -> None:
    if not path.parent.exists():
        os.makedirs(path.parent)
    with open(path, "w", newline="", encoding="utf-8") as bom_csv:
        rows = make_bom(components)
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
        if bomline.LCSC_Partnumber in [row.LCSC_Partnumber for row in compact_bomlines]:
            continue

        compact_bomline = bomline
        for other_bomline in bomlines[row + 1 :]:
            if bomline.LCSC_Partnumber == other_bomline.LCSC_Partnumber:
                for key in "Footprint", "Value":
                    if getattr(bomline, key) != getattr(other_bomline, key):
                        logger.warning(
                            f"{key} is not the same for two equal partnumbers "
                            f"{bomline.LCSC_Partnumber}: "
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


def _get_bomline(cmp: fabll.Node) -> BOMLine | None:
    if not cmp.has_trait(F.Footprints.has_associated_footprint):
        logger.warning(f"Missing associated footprint on component '{cmp}'")
        return
    # TODO make extra trait for this
    if cmp.has_trait(F.has_part_picked) and isinstance(
        cmp.get_trait(F.has_part_picked), F.has_part_removed
    ):
        return

    if missing := [
        t.__name__
        for t in (
            F.has_part_picked,
            F.has_designator,
        )
        if not cmp.has_trait(t)
    ]:
        logger.warning(f"Missing fields on component '{cmp}': {missing}")
        return

    part = cmp.get_trait(F.has_part_picked).get_part()
    footprint = cmp.get_children(
        direct_only=False,
        types=fabll.Node,
        required_trait=F.KiCadFootprints.is_kicad_footprint,
    )[0]

    value = (
        cmp.get_trait(F.has_simple_value_representation).get_value()
        if cmp.has_trait(F.has_simple_value_representation)
        else ""
    )
    designator = cmp.get_trait(F.has_designator).get_designator() or ""

    if not isinstance(part, PickedPartLCSC):
        logger.warning(f"Non-LCSC parts not supported in JLCPCB BOM: {part}")
        return

    manufacturer = part.manufacturer
    partnumber = part.partno

    footprint_name = footprint.get_trait(
        F.KiCadFootprints.is_kicad_footprint
    ).get_kicad_footprint_name()

    return BOMLine(
        Designator=designator,
        Footprint=footprint_name,
        Quantity=1,
        Value=value,
        Manufacturer=manufacturer,
        Partnumber=partnumber,
        LCSC_Partnumber=part.lcsc_id,
    )


def test_get_bomline():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestNode(fabll.Node):
        class TestFootprint(fabll.Node):
            is_kicad_footprint = fabll.Traits.MakeEdge(
                F.KiCadFootprints.is_kicad_footprint.MakeChild(
                    kicad_identifier="test_lib:R_0402_1005Metric",
                    # pinmap={}, #TODO
                )
            )

        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _has_designator = fabll.Traits.MakeEdge(F.has_designator.MakeChild("R1"))
        _has_part_picked = fabll.Traits.MakeEdge(
            F.has_part_picked.MakeChild(
                PickedPartLCSC(
                    manufacturer="Amazing manufacturer",
                    partno="ABC-Part",
                    supplier_partno="12345",
                )
            )
        )
        _has_associated_footprint = fabll.Traits.MakeEdge(
            F.Footprints.has_associated_footprint.MakeChild(fabll.Node.MakeChild())
        )
        fp = TestFootprint.MakeChild()

    node = TestNode.bind_typegraph(tg).create_instance(g=g)

    bomline = _get_bomline(node)

    assert bomline is not None
    assert bomline.Designator == "R1"
    assert bomline.Footprint == "R_0402_1005Metric"
    assert bomline.Value == ""
    assert bomline.Manufacturer == "Amazing manufacturer"
    assert bomline.Partnumber == "ABC-Part"
