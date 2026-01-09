# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from enum import StrEnum

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.kicad.fileformats import Property
from faebryk.libs.picker.lcsc import PickedPart, PickedPartLCSC
from faebryk.libs.picker.lcsc import attach as lcsc_attach

NO_LCSC_DISPLAY = "No LCSC number"

logger = logging.getLogger(__name__)


class Properties(StrEnum):
    manufacturer = "Manufacturer"  # component manufacturer
    manufacturer_partno = "Partnumber"  # manufacturer part number
    supplier_partno = "LCSC"  # LCSC part number
    param_prefix = "PARAM_"
    # used in transformer
    param_wildcard = "PARAM_*"


def load_part_info_from_pcb(tg: fbrk.TypeGraph):
    """
    Load descriptive properties from footprints and saved parameters.
    """
    nodes_with_fp = [
        (n, n.get_trait(F.Footprints.has_associated_footprint).get_footprint())
        for n in fabll.Traits.get_implementor_objects(
            F.Footprints.has_associated_footprint.bind_typegraph(tg)
        )
    ]

    for node, fp_t in nodes_with_fp:
        assert node.has_trait(fabll.is_module)
        if node.has_trait(F.Pickable.has_part_picked):
            logger.warning(f"Skipping {node.get_name()} because it has part picked")
            continue
        assert F.SerializableMetadata.get_properties(node), "Should load when linking"

        part_props = [
            Properties.supplier_partno,
            Properties.manufacturer,
            Properties.manufacturer_partno,
        ]
        if not (
            k_pcb_fp_t := fp_t.try_get_trait(
                F.KiCadFootprints.has_associated_kicad_pcb_footprint
            )
        ):
            logger.warning(
                f"Skipping {node.get_name()} because it has no PCB footprint"
            )
            continue
        fp = k_pcb_fp_t.get_footprint()
        fp_props = {
            k.value: v
            for k in part_props
            if (v := Property.try_get_property(fp.propertys, k.value))
        }
        if fp_props.get(Properties.supplier_partno) == NO_LCSC_DISPLAY:
            del fp_props[Properties.supplier_partno]
        props = F.SerializableMetadata.get_properties(node)

        # check if node has changed
        if any(props.get(k.value) != fp_props.get(k.value) for k in part_props):
            logger.warning(f"Skipping {node.get_name()} because it has changed")
            continue

        lcsc_id = props.get(Properties.supplier_partno)
        manufacturer = props.get(Properties.manufacturer)
        partno = props.get(Properties.manufacturer_partno)

        # Load Part from PCB
        if lcsc_id and manufacturer and partno:
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.Pickable.has_part_picked
            ).setup(
                PickedPartLCSC(
                    supplier_partno=lcsc_id,
                    manufacturer=manufacturer,
                    partno=partno,
                )
            )
        elif lcsc_id:
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.Pickable.is_pickable_by_supplier_id
            ).setup(
                supplier_part_id=lcsc_id,
                supplier=F.Pickable.is_pickable_by_supplier_id.Supplier.LCSC,
            )
        elif manufacturer and partno:
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.Pickable.is_pickable_by_part_number
            ).setup(manufacturer=manufacturer, partno=partno)
        else:
            raise ValueError(f"No part info found for {node.get_name()}")

        if lcsc_id:
            module_with_fp = node.try_get_trait(F.Footprints.can_attach_to_footprint)
            if module_with_fp is None:
                raise Exception(
                    f"Module {node.get_full_name(types=True)} does not have "
                    "can_attach_to_footprint trait",
                    node,
                )
            lcsc_attach(module_with_fp, lcsc_id)

        if "Datasheet" in fp_props:
            fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.has_datasheet
            ).setup(datasheet=fp_props["Datasheet"])

        # Load saved parameters from descriptive properties
        for key, value in props.items():
            if not key.startswith(Properties.param_prefix):
                logger.warning(
                    f"Skipping {key} because it doesn't start with "
                    f"{Properties.param_prefix}"
                )
                continue

            param_name = key.removeprefix(Properties.param_prefix)
            # Skip if parameter doesn't exist in node
            param_child = fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=node.instance, child_identifier=param_name
            )
            if param_child is None:
                logger.warning(
                    f"Parameter {param_name} not found in node {node.get_name()}"
                )
                continue
            param = fabll.Node.bind_instance(param_child)
            # Skip if not a parameter
            if not param.has_trait(F.Parameters.is_parameter):
                logger.warning(f"{param_name} in {node.get_name()} is not a parameter")
                continue
            param_value = json.loads(value)
            param_lit = F.Literals.is_literal.deserialize(
                param_value, g=node.g, tg=node.tg
            )
            # Alias the parameter to the deserialized literal
            param.get_trait(F.Parameters.is_parameter_operatable).set_subset(
                g=node.g, value=param_lit.switch_cast()
            )


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
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
    from faebryk.libs.kicad.fileformats import kicad
    from faebryk.libs.test.fileformats import PCBFILE

    pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE).kicad_pcb
    k_pcb_fp = pcb.footprints[1]

    # Add required part properties to the footprint
    test_lcsc = "C123456"
    test_mfr = "blaze-it-inc"
    test_partno = "69420"
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
    k_pcb_fp.propertys.append(
        kicad.pcb.Property(
            name="Manufacturer",
            value=test_mfr,
            at=at,
            layer="F.Fab",
            uuid=kicad.gen_uuid(),
            hide=True,
            effects=None,
            unlocked=None,
        )
    )
    k_pcb_fp.propertys.append(
        kicad.pcb.Property(
            name="Partnumber",
            value=test_partno,
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

    # Add SerializableMetadata as traits to simulate previous build
    data = {
        Properties.supplier_partno.value: test_lcsc,
        Properties.manufacturer.value: test_mfr,
        Properties.manufacturer_partno.value: test_partno,
    }
    fabll.Traits.create_and_add_instance_to(res_node, F.SerializableMetadata).setup(
        data
    )

    fp_node = fabll.Node.bind_typegraph(tg).create_instance(g=g)
    fp = fabll.Traits.create_and_add_instance_to(fp_node, F.Footprints.is_footprint)

    transformer = PCB_Transformer(pcb, app)

    fabll.Traits.create_and_add_instance_to(
        fp, F.KiCadFootprints.has_associated_kicad_pcb_footprint
    ).setup(k_pcb_fp, transformer)
    fabll.Traits.create_and_add_instance_to(
        res_node, F.Footprints.has_associated_footprint
    ).setup(footprint=fp)

    # Mock lcsc_attach to avoid network calls and project config requirements
    # Since this test is in the same module, we need to replace the global directly
    original_lcsc_attach = globals()["lcsc_attach"]
    globals()["lcsc_attach"] = lambda *args, **kwargs: None
    try:
        load_part_info_from_pcb(tg)
    finally:
        globals()["lcsc_attach"] = original_lcsc_attach

    picked_trait = res_node.get_trait(F.Pickable.has_part_picked)
    assert picked_trait is not None
    part = picked_trait.try_get_part()
    assert part is not None
    assert part.supplier_partno == test_lcsc
    assert part.manufacturer == test_mfr
    assert part.partno == test_partno
