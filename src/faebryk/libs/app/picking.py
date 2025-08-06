# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from enum import StrEnum

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.libs.picker.lcsc import PickedPartLCSC
from faebryk.libs.picker.lcsc import attach as lcsc_attach
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import KeyErrorNotFound

NO_LCSC_DISPLAY = "No LCSC number"

logger = logging.getLogger(__name__)


class Properties(StrEnum):
    manufacturer = "Manufacturer"
    partno = "Partnumber"
    lcsc = "LCSC"
    param_prefix = "PARAM_"
    # used in transformer
    param_wildcard = "PARAM_*"


def load_part_info_from_pcb(G: Graph):
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
        assert node.has_trait(F.has_descriptive_properties), "Should load when linking"

        part_props = [Properties.lcsc, Properties.manufacturer, Properties.partno]
        fp = trait.get_fp()
        fp_props = {k.value: v for k in part_props if (v := fp.try_get_property(k))}
        if fp_props.get(Properties.lcsc) == NO_LCSC_DISPLAY:
            del fp_props[Properties.lcsc]
        props = node.get_trait(F.has_descriptive_properties).get_properties()

        # check if node has changed
        if any(props.get(k.value) != fp_props.get(k.value) for k in part_props):
            continue

        lcsc_id = props.get(Properties.lcsc)
        manufacturer = props.get(Properties.manufacturer)
        partno = props.get(Properties.partno)

        # Load Part from PCB
        if lcsc_id and manufacturer and partno:
            node.add(
                F.has_part_picked(
                    PickedPartLCSC(
                        supplier_partno=lcsc_id,
                        manufacturer=manufacturer,
                        partno=partno,
                    )
                )
            )
        elif lcsc_id:
            node.add(
                F.has_explicit_part.by_supplier(
                    supplier_partno=lcsc_id,
                    supplier_id="lcsc",
                )
            )
        elif manufacturer and partno:
            node.add(
                F.has_explicit_part.by_mfr(
                    mfr=manufacturer,
                    partno=partno,
                )
            )

        if lcsc_id:
            lcsc_attach(node, lcsc_id)

        if "Datasheet" in fp_props:
            node.add(F.has_datasheet_defined(fp_props["Datasheet"]))

        # Load saved parameters from descriptive properties
        for key, value in props.items():
            if not key.startswith(Properties.param_prefix):
                continue

            param_name = key.removeprefix(Properties.param_prefix)
            # Skip if parameter doesn't exist in node
            try:
                param = node[param_name]
            except KeyErrorNotFound:
                logger.warning(
                    f"Parameter {param_name} not found in node {node.get_name()}"
                )
                continue
            param_value = json.loads(value)
            param_value = P_Set.deserialize(param_value)
            assert isinstance(param, Parameter)
            param.alias_is(param_value)


def save_part_info_to_pcb(G: Graph):
    """
    Save parameters to footprints (by copying them to descriptive properties).
    """

    nodes = GraphFunctions(G).nodes_with_trait(F.has_part_picked)

    for node, _ in nodes:
        if t := node.try_get_trait(F.has_part_picked):
            part = t.try_get_part()
            if part is None:
                continue
            if isinstance(part, PickedPartLCSC):
                node.add(
                    F.has_descriptive_properties_defined(
                        {Properties.lcsc: part.lcsc_id}
                    )
                )
                # TODO save info?
            node.add(
                F.has_descriptive_properties_defined(
                    {
                        Properties.manufacturer: part.manufacturer,
                        Properties.partno: part.partno,
                    }
                )
            )

        for p in node.get_children(direct_only=True, types=Parameter):
            lit = p.try_get_literal()
            if lit is None:
                continue
            lit = P_Set.from_value(lit)
            key = f"{Properties.param_prefix}{p.get_name()}"
            value = json.dumps(lit.serialize())
            node.add(F.has_descriptive_properties_defined({key: value}))
