# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

logger = logging.getLogger(__name__)


def _get_testpoints(app: Module) -> list[F.TestPoint]:
    return [
        testpoint
        for testpoint in app.get_children_modules(
            types=F.TestPoint,
            include_root=True,
        )
        if testpoint.has_trait(F.has_footprint)
        and testpoint.get_trait(F.has_footprint)
        .get_footprint()
        .has_trait(F.has_kicad_footprint)
    ]


def export_testpoints(
    app: Module,
    testpoints_file: Path,
):
    """
    Get all testpoints from the application and export their information to a JSON file
    """
    testpoint_data: dict[str, dict] = {}
    testpoints = _get_testpoints(app)

    for testpoint in testpoints:
        designator = testpoint.get_trait(F.has_designator).get_designator()
        full_name = testpoint.get_full_name()
        fp = testpoint.get_trait(F.has_footprint).get_footprint()
        footprint = PCB_Transformer.get_fp(fp)  # get KiCad footprint
        position = footprint.at
        layer = footprint.layer
        library_name = footprint.name

        # Get single connected net name
        net = F.Net.find_named_net_for_mif(testpoint.contact)
        net_name = net.get_trait(F.has_overriden_name).get_name() if net else "no-net"

        testpoint_data[designator] = {
            "testpoint_name": full_name,
            "net_name": net_name,
            "footprint_name": library_name,
            "position": {"x": position.x, "y": position.y, "rotation": position.r},
            "layer": layer,
        }

    with open(testpoints_file, "w", encoding="utf-8") as f:
        json.dump(obj=testpoint_data, fp=f, indent=4)
