# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from enum import StrEnum

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.kicad.fileformats import Property, kicad
from faebryk.libs.picker.lcsc import PickedPart, PickedPartLCSC

NO_LCSC_DISPLAY = "No LCSC number"

logger = logging.getLogger(__name__)


class Properties(StrEnum):
    manufacturer = "Manufacturer"  # component manufacturer
    manufacturer_partno = "Partnumber"  # manufacturer part number
    supplier_partno = "LCSC"  # LCSC part number
    param_prefix = "PARAM_"
    # used in transformer
    param_wildcard = "PARAM_*"


def load_part_info_from_pcb(pcb: kicad.pcb.KicadPcb, tg: fbrk.TypeGraph):
    """
    Load part constraints from PCB properties and set them on modules.

    This reads LCSC IDs and saved parameters from PCB footprint properties
    and sets them as constraints. The normal picker flow will then handle
    part selection and footprint creation via the part lifecycle manager.
    """
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

    # Map modules to PCB footprints by atopile address
    footprint_map = PCB_Transformer.map_footprints(tg, pcb)

    for node, pcb_fp in footprint_map.items():
        if node.has_trait(F.Pickable.has_part_picked):
            logger.debug(f"Skipping {node.get_name()} - already has part picked")
            continue
        if node.has_trait(F.has_part_removed):
            logger.debug(f"Skipping {node.get_name()} - has part removed")
            continue

        # Read part properties from PCB footprint
        lcsc_id = Property.try_get_property(
            pcb_fp.propertys, Properties.supplier_partno
        )
        if lcsc_id == NO_LCSC_DISPLAY:
            lcsc_id = None

        manufacturer = Property.try_get_property(
            pcb_fp.propertys, Properties.manufacturer
        )
        partno = Property.try_get_property(
            pcb_fp.propertys, Properties.manufacturer_partno
        )

        # Set picking constraint based on available info
        if lcsc_id:
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.Pickable.is_pickable_by_supplier_id
            ).setup(
                supplier_part_id=lcsc_id,
                supplier=F.Pickable.is_pickable_by_supplier_id.Supplier.LCSC,
            )
            logger.debug(f"Set LCSC constraint {lcsc_id} on {node.get_name()}")
        elif manufacturer and partno:
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.Pickable.is_pickable_by_part_number
            ).setup(manufacturer=manufacturer, partno=partno)
            logger.debug(
                f"Set part number constraint {manufacturer}/{partno} "
                f"on {node.get_name()}"
            )
        else:
            logger.warning(f"No part info found in PCB for {node.get_name()}")
            continue

        # Load saved parameters as subset constraints
        for prop in pcb_fp.propertys:
            if not prop.name.startswith(Properties.param_prefix):
                continue

            param_name = prop.name.removeprefix(Properties.param_prefix)
            # Skip if parameter doesn't exist in node
            param_child = fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=node.instance, child_identifier=param_name
            )
            if param_child is None:
                logger.debug(
                    f"Parameter {param_name} not found in node {node.get_name()}"
                )
                continue
            param = fabll.Node.bind_instance(param_child)
            # Skip if not a parameter
            if not param.has_trait(F.Parameters.is_parameter):
                logger.debug(f"{param_name} in {node.get_name()} is not a parameter")
                continue

            param_value = json.loads(prop.value)
            param_lit = F.Literals.is_literal.deserialize(
                param_value, g=node.g, tg=node.tg
            )
            # Constrain the parameter to the saved literal
            param.get_trait(F.Parameters.is_parameter_operatable).set_subset(
                g=node.g, value=param_lit.switch_cast()
            )
            logger.debug(f"Set parameter constraint {param_name} on {node.get_name()}")


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

    # TODO we should pick by graph instead of by app?
    # nodes = fabll.Traits.get_implementor_objects(
    #    F.Pickable.has_part_picked.bind_typegraph(app.tg)
    # )

    if len(nodes) == 0:
        logger.warning("No nodes with part picked found")
        return

    for node in nodes:
        has_part_picked = node.get_trait(F.Pickable.has_part_picked)
        if has_part_picked.has_trait(F.has_part_removed):
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
    g = fabll.graph.GraphView.create()
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


def test_load_part_info_from_pcb():
    from faebryk.libs.test.fileformats import PCBFILE

    pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE).kicad_pcb
    k_pcb_fp = pcb.footprints[1]

    # Add required part properties to the footprint
    test_lcsc = "C123456"
    at = kicad.pcb.Xyr(x=0, y=0, r=0)
    k_pcb_fp.propertys.append(
        kicad.pcb.Property(
            name="LCSC",
            value=test_lcsc,
            at=at,
            layer="F.Fab",
            uuid=kicad.gen_uuid(),
            hide=True,
            effects=None,
            unlocked=None,
        )
    )
    # Add atopile_address property to match the node
    k_pcb_fp.propertys.append(
        kicad.pcb.Property(
            name="atopile_address",
            value="res",
            at=at,
            layer="F.Fab",
            uuid=kicad.gen_uuid(),
            hide=True,
            effects=None,
            unlocked=None,
        )
    )

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _TestApp(fabll.Node):
        is_module_ = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        res = F.Resistor.MakeChild()

    app = _TestApp.bind_typegraph(tg).create_instance(g=g)
    res_node = app.res.get()

    # Call load_part_info_from_pcb - now it sets is_pickable_by_supplier_id
    load_part_info_from_pcb(pcb, tg)

    # Check that is_pickable_by_supplier_id was set (not has_part_picked)
    pickable_trait = res_node.try_get_trait(F.Pickable.is_pickable_by_supplier_id)
    assert pickable_trait is not None
    assert pickable_trait.get_supplier_part_id() == test_lcsc
    assert (
        pickable_trait.get_supplier()
        == F.Pickable.is_pickable_by_supplier_id.Supplier.LCSC.name
    )
