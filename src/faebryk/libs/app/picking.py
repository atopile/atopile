# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Part picking utilities for saving/loading part info to/from PCB.

Note: Loading PCB constraints and invalidation logic is in keep_picked_parts.py
"""

import json
import logging
from enum import StrEnum

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.picker.lcsc import PickedPart, PickedPartLCSC

logger = logging.getLogger(__name__)


class Properties(StrEnum):
    manufacturer = "Manufacturer"  # component manufacturer
    manufacturer_partno = "Partnumber"  # manufacturer part number
    supplier_partno = "LCSC"  # LCSC part number
    param_prefix = "PARAM_"
    # used in transformer
    param_wildcard = "PARAM_*"


def save_part_info_to_pcb(app: fabll.Node):
    """
    Save parameters to footprints (by copying them to descriptive properties).
    """

    nodes = app.get_children(
        direct_only=False,
        types=fabll.Node,
        include_root=True,
        required_trait=F.Pickable.has_part_picked,
    )

    if len(nodes) == 0:
        logger.warning("No nodes with part picked found")
        return

    for node in nodes:
        has_part_picked = node.get_trait(F.Pickable.has_part_picked)
        if has_part_picked.is_removed():
            continue

        part = has_part_picked.try_get_part()
        if part is None:
            logger.warning(f"No part found for {node.get_name()}")
            continue

        data: dict[str, str] = {}
        if isinstance(part, (PickedPart, PickedPartLCSC)):
            data[Properties.supplier_partno] = part.supplier_partno
        data[Properties.manufacturer] = part.manufacturer
        data[Properties.manufacturer_partno] = part.partno

        for p in node.get_children(
            direct_only=True,
            types=fabll.Node,
            required_trait=F.Parameters.is_parameter,
        ):
            lit = p.get_trait(F.Parameters.is_parameter_operatable).try_extract_subset()
            if lit is None:
                continue
            data[f"{Properties.param_prefix}{p.get_name()}"] = json.dumps(
                lit.serialize(), ensure_ascii=False
            )
        fabll.Traits.create_and_add_instance_to(node, F.SerializableMetadata).setup(
            data
        )


def test_save_part_info_to_pcb():
    from faebryk.core import graph

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    res = F.Resistor.bind_typegraph(tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(res, F.Pickable.has_part_picked).setup(
        PickedPartLCSC(
            supplier_partno="C123456", manufacturer="blaze-it-inc", partno="69420"
        )
    )

    save_part_info_to_pcb(res)

    # Convert traits to dictionary for easier checking
    trait_dict = F.SerializableMetadata.get_properties(res)

    # Assert expected key:value pairs
    assert trait_dict.get(Properties.manufacturer.value) == "blaze-it-inc"
    assert trait_dict.get(Properties.manufacturer_partno.value) == "69420"
