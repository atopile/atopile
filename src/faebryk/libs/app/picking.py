# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.exporters.pcb.kicad.pcb import NO_LCSC_DISPLAY
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

logger = logging.getLogger(__name__)


def load_descriptive_properties(G: Graph):
    """
    Load descriptive properties from footprints.
    """

    nodes = GraphFunctions(G).nodes_with_trait(
        PCB_Transformer.has_linked_kicad_footprint
    )

    for node, trait in nodes:
        if node.has_trait(F.has_part_picked):
            continue
        if (
            node.has_trait(F.has_descriptive_properties)
            and "LCSC" in node.get_trait(F.has_descriptive_properties).get_properties()
        ):
            continue

        fp = trait.get_fp()
        lcsc_display_prop = fp.propertys.get("LCSC")
        if not lcsc_display_prop:
            continue

        lcsc_display = lcsc_display_prop.value
        if lcsc_display == NO_LCSC_DISPLAY:
            continue

        # node.add(F.has_explicit_part.by_supplier(lcsc_display, supplier_id="lcsc"))
        node.add(F.has_descriptive_properties_defined({"LCSC": lcsc_display}))
