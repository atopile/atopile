import csv
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from faebryk.core.core import Module
from faebryk.library.has_descriptive_properties import has_descriptive_properties
from faebryk.library.has_designator import has_designator
from faebryk.library.has_footprint import has_footprint
from faebryk.library.has_kicad_footprint import has_kicad_footprint
from faebryk.library.has_simple_value_representation import (
    has_simple_value_representation,
)
from faebryk.libs.picker.picker import DescriptiveProperties

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


def rename_column(rows: list[dict[str, str]], old: str, new: str) -> None:
    for row in rows:
        row[new] = row.pop(old)


def write_bom_jlcpcb(components: set[Module], path: Path) -> None:
    if not path.parent.exists():
        os.makedirs(path.parent)
    with open(path, "w", newline="") as bom_csv:
        bomlines = [line for c in components if (line := _get_bomline(c))]
        bomlines = sorted(_compact_bomlines(bomlines), key=lambda x: x.Designator)

        rows = [vars(line) for line in bomlines]
        rename_column(rows, "LCSC_Partnumber", "LCSC Part #")

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
                            f"with {key}: {getattr(other_bomline,key)}"
                        )
                compact_bomline.Designator = ", ".join(
                    sorted(
                        (
                            compact_bomline.Designator + ", " + other_bomline.Designator
                        ).split(", ")
                    )
                )
                compact_bomline.Quantity += other_bomline.Quantity
        compact_bomlines += [compact_bomline]

    return compact_bomlines


def _get_bomline(cmp: Module) -> BOMLine | None:
    if not cmp.has_trait(has_footprint):
        return

    if not all(
        cmp.has_trait(t)
        for t in (
            has_descriptive_properties,
            has_designator,
        )
    ):
        logger.warning(f"Missing fields on component {cmp}")
        return

    properties = cmp.get_trait(has_descriptive_properties).get_properties()
    footprint = cmp.get_trait(has_footprint).get_footprint()

    value = (
        cmp.get_trait(has_simple_value_representation).get_value()
        if cmp.has_trait(has_simple_value_representation)
        else ""
    )
    designator = cmp.get_trait(has_designator).get_designator()

    if not footprint.has_trait(has_kicad_footprint):
        logger.warning(f"Missing kicad footprint on component {cmp}")
        return

    if "LCSC" not in properties:
        return

    manufacturer = (
        properties[DescriptiveProperties.manufacturer]
        if DescriptiveProperties.manufacturer in properties
        else ""
    )
    partnumber = (
        properties[DescriptiveProperties.partno]
        if DescriptiveProperties.partno in properties
        else ""
    )

    footprint_name = footprint.get_trait(has_kicad_footprint).get_kicad_footprint_name()

    return BOMLine(
        Designator=designator,
        Footprint=footprint_name,
        Quantity=1,
        Value=value,
        Manufacturer=manufacturer,
        Partnumber=partnumber,
        LCSC_Partnumber=properties["LCSC"],
    )
