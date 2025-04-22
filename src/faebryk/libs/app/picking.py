# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import KeyErrorNotFound

NO_LCSC_DISPLAY = "No LCSC number"

logger = logging.getLogger(__name__)


def load_descriptive_properties(G: Graph):
    """
    Load descriptive properties from footprints and saved parameters.
    """
    nodes = GraphFunctions(G).nodes_with_trait(
        PCB_Transformer.has_linked_kicad_footprint
    )

    for node, trait in nodes:
        assert isinstance(node, Module)
        if isinstance(node, F.Footprint):
            continue
        if node.has_trait(F.has_part_picked):
            continue

        fp = trait.get_fp()
        props = fp.propertys

        # Load LCSC number from descriptive properties
        if (
            F.has_descriptive_properties.get_from(node, "LCSC") is None
            and (lcsc_display_prop := props.get("LCSC")) is not None
            and (lcsc_display := lcsc_display_prop.value) != NO_LCSC_DISPLAY
        ):
            # node.add(F.has_explicit_part.by_supplier(lcsc_display,supplier_id="lcsc"))
            node.add(F.has_descriptive_properties_defined({"LCSC": lcsc_display}))

        # Load saved parameters from descriptive properties
        for key, value in props.items():
            if not key.startswith("PARAM_"):
                continue

            param_name = key.removeprefix("PARAM_")
            # Skip if parameter doesn't exist in node
            try:
                param = node[param_name]
            except KeyErrorNotFound:
                logger.warning(
                    f"Parameter {param_name} not found in node {node.get_name()}"
                )
                continue
            param_value = json.loads(value.value)
            param_value = P_Set.deserialize(param_value)
            assert isinstance(param, Parameter)
            param.alias_is(param_value)


def save_parameters(G: Graph):
    """
    Save parameters to footprints (by copying them to descriptive properties).
    """

    nodes = GraphFunctions(G).nodes_with_trait(F.has_part_picked)

    for node, _ in nodes:
        for p in node.get_children(direct_only=True, types=Parameter):
            lit = p.try_get_literal()
            if lit is None:
                continue
            lit = P_Set.from_value(lit)
            key = f"PARAM_{p.get_name()}"
            value = json.dumps(lit.serialize())
            node.add(F.has_descriptive_properties_defined({key: value}))
