# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path
from typing import Any, Callable

from faebryk.core.core import Module
from faebryk.core.graph import Graph
from faebryk.core.util import get_node_tree, iter_tree_by_depth
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import apply_route_in_pcb
from faebryk.library.has_pcb_layout import has_pcb_layout
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined import has_pcb_position_defined
from faebryk.library.has_pcb_routing_strategy import has_pcb_routing_strategy
from faebryk.libs.app.kicad_netlist import write_netlist
from faebryk.libs.kicad.pcb import PCB, Project, fp_lib_table

logger = logging.getLogger(__name__)


def apply_layouts(app: Module):
    if not app.has_trait(has_pcb_position):
        app.add_trait(
            has_pcb_position_defined(
                has_pcb_position.Point((0, 0, 0, has_pcb_position.layer_type.NONE))
            )
        )

    tree = get_node_tree(app)
    for level in iter_tree_by_depth(tree):
        for n in level:
            if n.has_trait(has_pcb_layout):
                n.get_trait(has_pcb_layout).apply()


def apply_routing(app: Module, transformer: PCB_Transformer):
    strategies: list[tuple[has_pcb_routing_strategy, int]] = []

    tree = get_node_tree(app)
    for i, level in enumerate(list(iter_tree_by_depth(tree))):
        for n in level:
            if not n.has_trait(has_pcb_routing_strategy):
                continue

            strategies.append((n.get_trait(has_pcb_routing_strategy), i))

    logger.info("Applying routes")

    # sort by (prio, level)
    for strategy, level in sorted(
        strategies, key=lambda x: (x[0].priority, x[1]), reverse=True
    ):
        logger.debug(f"{strategy} | {level=}")

        routes = strategy.calculate(transformer)
        for route in routes:
            apply_route_in_pcb(route, transformer)


def apply_design(
    pcb_path: Path,
    netlist_path: Path,
    G: Graph,
    app: Module,
    transform: Callable[[PCB_Transformer], Any] | None = None,
):
    logger.info(f"Writing netlist to {netlist_path}")
    changed = write_netlist(G, netlist_path, use_kicad_designators=True)
    apply_netlist(pcb_path, netlist_path, changed)

    logger.info("Load PCB")
    pcb = PCB.load(pcb_path)

    transformer = PCB_Transformer(pcb, G, app)

    logger.info("Transform PCB")
    if transform:
        transform(transformer)

    # set layout
    apply_layouts(app)
    transformer.move_footprints()
    apply_routing(app, transformer)

    logger.info(f"Writing pcbfile {pcb_path}")
    pcb.dump(pcb_path)

    print("Reopen PCB in kicad")


def include_footprints(pcb_path: Path):
    fplibpath = pcb_path.parent / "fp-lib-table"
    if fplibpath.exists():
        fptable = fp_lib_table.load(fplibpath)
    else:
        fptable = fp_lib_table.factory(version=7)

    # TODO make more generic, this is very lcsc specific
    from faebryk.libs.picker.lcsc import LIB_FOLDER as LCSC_LIB_FOLDER

    fppath = LCSC_LIB_FOLDER / "footprints/lcsc.pretty"
    relative = True
    try:
        fppath_rel = fppath.resolve().relative_to(
            pcb_path.parent.resolve(), walk_up=True
        )
        # check if not going up too much
        if len([part for part in fppath_rel.parts if part == ".."]) > 5:
            raise ValueError()
        fppath = fppath_rel
    except ValueError:
        relative = False

    if not any(fplib.name == "lcsc" for fplib in fptable.libs):
        fptable.add_lib(
            fp_lib_table.lib.factory(
                "lcsc",
                uri=str(fppath),
                uri_prj_relative=relative,
                descr="FBRK: LCSC footprints auto-downloaded",
            )
        )
        logger.warning(
            "Changed fp-lib-table to include lcsc library, need to restart pcbnew"
        )

    fptable.dump(fplibpath)


def apply_netlist(pcb_path: Path, netlist_path: Path, netlist_has_changed: bool = True):
    include_footprints(pcb_path)

    # Set netlist path in gui menu
    prj_path = pcb_path.with_suffix(".kicad_pro")
    if not prj_path.exists():
        project = Project()
    else:
        project = Project.load(prj_path)
    project.pcbnew.last_paths.netlist = str(
        netlist_path.resolve().relative_to(pcb_path.parent.resolve(), walk_up=True)
    )
    project.dump(prj_path)

    # Import netlist into pcb
    if netlist_has_changed:
        print(
            "Open the PCB in kicad and import the netlist.\n"
            "Then save the pcb and press ENTER.\n"
            f"PCB location: {pcb_path}"
        )
        input()
