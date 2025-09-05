# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

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


class PicksLoadError(Exception):
    pass


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
            if (lit := p.try_get_literal()) is None:
                continue
            lit = P_Set.from_value(lit)
            node.add(F.has_descriptive_properties_defined({p.get_name(): str(lit)}))


def load_picks_from_file(app: Module, picks_file_path: Path):
    from atopile.front_end import bob
    # TODO: does having the app in the graph twice kill performance?

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

    for node, t in GraphFunctions(app.get_graph()).nodes_with_trait(F.has_cached_pick):
        lcsc_id = cast_assert(PickedPartLCSC, t.get_part()).lcsc_id
        lcsc_attach(cast_assert(Module, node), lcsc_id)


def save_picks_to_file(G: Graph, picks_file_path: Path):
    # TODO: include params

    from atopile.config import config

    parts: dict[str, tuple[PickedPartLCSC, type[Module]]] = {}
    picks: dict[str, str] = {}

    for node, _ in GraphFunctions(G).nodes_with_trait(F.has_cacheable_pick):
        t = node.try_get_trait(F.has_part_picked)
        assert t is not None

        logger.info(f"Extracting pick for `{node.get_full_name()}`")

        part = cast_assert(PickedPartLCSC, t.get_part())
        part_identifier = (
            sanitize_name(part.manufacturer) + "_" + sanitize_name(part.partno)
        )

        assert isinstance(node, Module)
        node_type = type(
            node.get_less_special() if node.has_trait(F.has_cached_pick) else node
        )

        parts[part_identifier] = (part, node_type)
        picks[node.get_full_name()] = part_identifier

    picks_file = AtoCodeGen.PicksFile(
        entry=config.build.entry_section,
        file=config.build.entry_file_path.relative_to(config.project.paths.src),
    )

    for identifier, (part, node_type) in natsorted(parts.items()):
        logger.info(f"Saving definition for part `{identifier}`")

        # TODO: import model from parts/... instead
        picks_file.add_pick_type(
            name=identifier,
            from_name=node_type.__name__,  #  FIXME: import path if not stdlib?
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
        logger.info(f"Saving pick for `{address}`")
        picks_file.add_pick(AtoCodeGen.Retype(address=address, type=picks[name]))

    logger.info(f"Writing picks file to `{picks_file_path}`")
    picks_file_path.write_text(picks_file.dump(), encoding="utf-8")
