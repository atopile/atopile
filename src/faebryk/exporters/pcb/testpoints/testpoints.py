# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)


def _get_testpoint_packages(
    app: fabll.Node,
) -> list[tuple[fabll.Node, fabll.Node]]:
    """
    Find testpoint packages: nodes with has_associated_footprint and TP designator
    prefix. Returns (parent_testpoint, package) tuples.
    """
    result = []
    for node in fabll.Traits.get_implementor_objects(
        trait=F.Footprints.has_associated_footprint.bind_typegraph(app.tg)
    ):
        # Check for TP designator prefix
        prefix_trait = node.try_get_trait(F.has_designator_prefix)
        if not prefix_trait:
            continue
        if prefix_trait.get_prefix() != F.has_designator_prefix.Prefix.TP:
            continue

        # Check that the footprint has a KiCad PCB footprint bound
        fp = node.get_trait(F.Footprints.has_associated_footprint).get_footprint()
        if not fp.has_trait(F.KiCadFootprints.has_associated_kicad_pcb_footprint):
            continue

        # Navigate to the parent (the TestPoint module)
        parent_info = node.get_parent()
        if parent_info is None:
            continue
        parent = parent_info[0]

        result.append((parent, node))
    return result


def export_testpoints(
    app: fabll.Node,
    testpoints_file: Path,
):
    """
    Get all testpoints from the application and export their information to a JSON file
    """
    testpoint_data: dict[str, dict] = {}
    testpoints = _get_testpoint_packages(app)

    for testpoint, package in testpoints:
        designator = not_none(package.get_trait(F.has_designator).get_designator())
        full_name = testpoint.get_full_name()
        fp = package.get_trait(F.Footprints.has_associated_footprint).get_footprint()
        footprint = PCB_Transformer.get_kicad_pcb_fp(fp)
        position = footprint.at
        layer = footprint.layer
        library_name = footprint.name

        # Get net name from the PCB footprint's pad
        net_name = "no-net"
        for pad in footprint.pads:
            if pad.net is not None and pad.net.name:
                net_name = pad.net.name
                break

        testpoint_data[designator] = {
            "testpoint_name": full_name,
            "net_name": net_name,
            "footprint_name": library_name,
            "position": {"x": position.x, "y": position.y, "rotation": position.r},
            "layer": layer,
        }

    with open(testpoints_file, "w", encoding="utf-8") as f:
        json.dump(obj=testpoint_data, fp=f, indent=4)
