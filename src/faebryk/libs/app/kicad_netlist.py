# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from faebryk.core.graph import Graph
from faebryk.exporters.netlist.graph import attach_nets_and_kicad_info
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.exporters.netlist.netlist import make_t2_netlist_from_graph
from faebryk.importers.netlist.kicad.netlist_kicad import to_faebryk_t2_netlist
from faebryk.libs.app.designators import (
    attach_random_designators,
    load_designators_from_netlist,
    override_names_with_designators,
)

logger = logging.getLogger(__name__)


def write_netlist(
    G: Graph, netlist_path: Path, use_kicad_designators: bool = False
) -> bool:
    if use_kicad_designators:
        logger.info("Determining kicad-style designators")
        # use kicad designators & names
        if netlist_path.exists():
            load_designators_from_netlist(
                G,
                {
                    c.name: c
                    for c in to_faebryk_t2_netlist(netlist_path.read_text())["comps"]
                },
            )
        attach_random_designators(G)
        override_names_with_designators(G)

    logger.info("Creating Nets and attach kicad info")
    attach_nets_and_kicad_info(G)

    logger.info("Making faebryk netlist")
    t2 = make_t2_netlist_from_graph(G)
    logger.info("Making kicad netlist")
    netlist = from_faebryk_t2_netlist(t2)

    if netlist_path.exists():
        old_netlist = netlist_path.read_text()
        # pure text based check
        # works in a lot of cases because netlist is pretty stable
        # components sorted by name
        # nets sorted by name
        if old_netlist == netlist:
            logger.warning("Netlist did not change, not writing")
            return False
        backup_path = netlist_path.with_suffix(netlist_path.suffix + ".bak")
        logger.info(f"Backup old netlist at {backup_path}")
        backup_path.write_text(old_netlist)

    assert isinstance(netlist, str)
    logger.info("Writing Experiment netlist to {}".format(netlist_path.resolve()))
    netlist_path.parent.mkdir(parents=True, exist_ok=True)
    netlist_path.write_text(netlist, encoding="utf-8")

    return True
