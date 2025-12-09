# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from enum import StrEnum

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.kicad.fileformats import Property
from faebryk.libs.picker.lcsc import PickedPartLCSC
from faebryk.libs.picker.lcsc import attach as lcsc_attach
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


def load_part_info_from_pcb(G: graph.GraphView):
    """
    Load descriptive properties from footprints and saved parameters.
    """
    nodes = fabll.Node.bind_typegraph(G).nodes_with_trait(
        F.KiCadFootprints.has_associated_kicad_pcb_footprint
    )

    for node, trait in nodes:
        assert node.has_trait(fabll.is_module)
        if isinstance(node, F.Footprints.GenericFootprint):
            continue
        if node.has_trait(F.has_part_picked):
            continue
        assert F.SerializableMetadata.get_properties(node), "Should load when linking"

        part_props = [Properties.lcsc, Properties.manufacturer, Properties.partno]
        fp = trait.get_fp()
        fp_props = {
            k.value: v
            for k in part_props
            if (v := Property.try_get_property(fp.propertys, k.value))
        }
        if fp_props.get(Properties.lcsc) == NO_LCSC_DISPLAY:
            del fp_props[Properties.lcsc]
        props = F.SerializableMetadata.get_properties(node)

        # check if node has changed
        if any(props.get(k.value) != fp_props.get(k.value) for k in part_props):
            continue

        lcsc_id = props.get(Properties.lcsc)
        manufacturer = props.get(Properties.manufacturer)
        partno = props.get(Properties.partno)

        # Load Part from PCB
        if lcsc_id and manufacturer and partno:
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.has_part_picked
            ).setup(
                PickedPartLCSC(
                    supplier_partno=lcsc_id,
                    manufacturer=manufacturer,
                    partno=partno,
                )
            )
        elif lcsc_id:
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.has_explicit_part
            ).setup_by_supplier(
                supplier_partno=lcsc_id,
                supplier_id="lcsc",
            )
        elif manufacturer and partno:
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.has_explicit_part
            ).setup_by_mfr(
                mfr=manufacturer,
                partno=partno,
            )
        else:
            raise ValueError(f"No part info found for {node.get_name()}")

        if lcsc_id:
            lcsc_attach(node, lcsc_id)

        if "Datasheet" in fp_props:
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.has_datasheet
            ).setup(datasheet=fp_props["Datasheet"])

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
            param_value = F.Literals.Numbers.deserialize(param_value)
            assert isinstance(param, Parameter)
            param.alias_is(param_value)


def save_part_info_to_pcb(g: graph.GraphView, tg: fbrk.TypeGraph):
    """
    Save parameters to footprints (by copying them to descriptive properties).
    """

    nodes = fabll.Traits.get_implementor_objects(F.has_part_picked.bind_typegraph(tg))

    for node in nodes:
        part = node.get_trait(F.has_part_picked).try_get_part()

        if part is None:
            continue

        if isinstance(part, PickedPartLCSC):
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.SerializableMetadata
            ).setup(key=Properties.lcsc, value=part.lcsc_id)

        fabll.Traits.create_and_add_instance_to(
            node=node, trait=F.SerializableMetadata
        ).setup(key=Properties.manufacturer, value=part.manufacturer)
        fabll.Traits.create_and_add_instance_to(
            node=node, trait=F.SerializableMetadata
        ).setup(key=Properties.partno, value=part.partno)

        for p in node.get_children(direct_only=True, types=F.Parameters.is_parameter):
            lit = p.try_get_literal()
            if lit is None:
                continue
            lit = F.Literals.Numbers.setup_from_singleton(value=lit)
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.SerializableMetadata
            ).setup(
                key=f"{Properties.param_prefix}{p.get_name()}",
                value=json.dumps(lit.serialize()),
            )


def test_save_part_info_to_pcb():
    print("")
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    res = F.Resistor.bind_typegraph(tg).create_instance(g=g)
    fabll.Traits.create_and_add_instance_to(res, F.has_part_picked).setup(
        PickedPartLCSC(
            supplier_partno="C123456", manufacturer="blaze-it-inc", partno="69420"
        )
    )

    save_part_info_to_pcb(g, tg)

    traits = fabll.Traits.get_implementors(F.SerializableMetadata.bind_typegraph(tg))

    # Convert traits to dictionary for easier checking
    trait_dict = {trait.key: trait.value for trait in traits}

    # Assert expected key:value pairs
    assert trait_dict.get(Properties.manufacturer.value) == "blaze-it-inc"
    assert trait_dict.get(Properties.partno.value) == "69420"
