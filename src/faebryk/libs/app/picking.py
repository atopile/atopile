# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from enum import StrEnum
from pathlib import Path

from natsort import natsorted

import faebryk.library._F as F
from atopile.datatypes import TypeRef
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.core.parameter import Parameter
from faebryk.core.trait import Trait
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.libs.codegen.atocodegen import AtoCodeGen, sanitize_name
from faebryk.libs.picker.lcsc import PickedPartLCSC
from faebryk.libs.picker.lcsc import attach as lcsc_attach
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import KeyErrorNotFound, cast_assert

NO_LCSC_DISPLAY = "No LCSC number"

logger = logging.getLogger(__name__)


class Properties(StrEnum):
    manufacturer = "Manufacturer"
    partno = "Partnumber"
    lcsc = "LCSC"
    param_prefix = "PARAM_"
    # used in transformer
    param_wildcard = "PARAM_*"


class PicksLoadError(Exception):
    pass


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


def load_picks_from_file(app: Module, picks_file_path: Path):
    from atopile.front_end import bob

    try:
        picks: Node = bob.build_file(
            picks_file_path,
            TypeRef.from_one(AtoCodeGen.PicksFile.PICKS_MODULE_NAME),
        )
    except FileNotFoundError as ex:
        raise PicksLoadError(f"File not found: {picks_file_path}") from ex

    assert isinstance(picks, Module)

    try:
        app_with_picks = picks.get_child_by_name("app")
    except KeyErrorNotFound:
        raise PicksLoadError("Field `app` not found")

    assert isinstance(app_with_picks, Module)

    app.specialize(app_with_picks)

    # TODO: skip if descriptive properties have changed
    # TODO: lcsc_attach


def _find_stdlib_ancestor(node: Module) -> type[Node]:
    # FIXME: handle non-trivial inheritance hierarchies
    while type(node).__name__ not in F.__dict__:
        node = node.get_less_special()
    return type(node)


def save_picks_to_file(G: Graph, picks_file_path: Path):
    # TODO: fix docstrings (has_descriptive_properties?)
    # TODO: save datasheet url (has_datasheet_defined)
    # TODO: include params
    # FIXME: skip parts that already have a pick (e.g. auto-generated packages) (has_suggested_pick)

    from atopile.config import config

    nodes: list[tuple[Node, Trait]] = GraphFunctions(G).nodes_with_trait(
        F.has_part_picked
    )

    parts: dict[str, tuple[PickedPartLCSC, type[Node]]] = {}
    picks: dict[str, str] = {}

    for node, _ in nodes:
        if t := node.try_get_trait(F.has_part_picked):
            part = cast_assert(PickedPartLCSC, t.get_part())
            part_identifier = (
                sanitize_name(part.manufacturer) + "_" + sanitize_name(part.partno)
            )

            node_type = _find_stdlib_ancestor(cast_assert(Module, node))

            parts[part_identifier] = (part, node_type)
            picks[node.get_full_name()] = part_identifier

    picks_file = AtoCodeGen.PicksFile(
        entry=config.build.entry_section,
        file=config.build.entry_file_path.relative_to(config.project.paths.src),
    )

    for identifier, (part, node_type) in natsorted(parts.items()):
        picks_file.add_pick_type(
            name=identifier,
            from_name=node_type.__name__,
            description=part.info.description if part.info is not None else "",
            pick_args={
                "supplier_id": "lcsc",
                "supplier_partno": part.lcsc_id,
                "manufacturer": part.manufacturer,
                "partno": part.partno,
            },
        )

    for name in natsorted(picks):
        address = "app." + name.removeprefix("app.")
        picks_file.add_pick(AtoCodeGen.Retype(address=address, type=picks[name]))

    with open(picks_file_path, "w") as f:
        f.write(picks_file.dump())
