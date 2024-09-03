# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable

import faebryk.library._F as F
from faebryk.core.graph import Graph
from faebryk.core.module import Module
from faebryk.core.util import get_node_tree, iter_tree_by_depth
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import apply_route_in_pcb
from faebryk.libs.app.kicad_netlist import write_netlist
from faebryk.libs.kicad.fileformats import (
    C_kicad_fp_lib_table_file,
    C_kicad_pcb_file,
    C_kicad_project_file,
)

logger = logging.getLogger(__name__)


def apply_layouts(app: Module):
    if not app.has_trait(F.has_pcb_position):
        app.add(
            F.has_pcb_position_defined(
                F.has_pcb_position.Point((0, 0, 0, F.has_pcb_position.layer_type.NONE))
            )
        )

    tree = get_node_tree(app)
    for level in iter_tree_by_depth(tree):
        for n in level:
            if n.has_trait(F.has_pcb_layout):
                n.get_trait(F.has_pcb_layout).apply()


def apply_routing(app: Module, transformer: PCB_Transformer):
    strategies: list[tuple[F.has_pcb_routing_strategy, int]] = []

    tree = get_node_tree(app)
    for i, level in enumerate(list(iter_tree_by_depth(tree))):
        for n in level:
            if not n.has_trait(F.has_pcb_routing_strategy):
                continue

            strategies.append((n.get_trait(F.has_pcb_routing_strategy), i))

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
    pcb = C_kicad_pcb_file.loads(pcb_path)

    transformer = PCB_Transformer(pcb.kicad_pcb, G, app)

    logger.info("Transform PCB")
    if transform:
        transform(transformer)

    # set layout
    apply_layouts(app)
    transformer.move_footprints()
    apply_routing(app, transformer)

    logger.info(f"Writing pcbfile {pcb_path}")
    pcb.dumps(pcb_path)

    print("Reopen PCB in kicad")


def include_footprints(pcb_path: Path):
    fplibpath = pcb_path.parent / "fp-lib-table"
    if fplibpath.exists():
        fptable = C_kicad_fp_lib_table_file.loads(fplibpath)
    else:
        fptable = C_kicad_fp_lib_table_file(
            C_kicad_fp_lib_table_file.C_fp_lib_table(version=7, libs=[])
        )

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

    uri = str(fppath)
    if relative:
        assert not uri.startswith("/")
        assert not uri.startswith("${KIPRJMOD}")
        uri = "${KIPRJMOD}/" + uri

    if not any(fplib.name == "lcsc" for fplib in fptable.fp_lib_table.libs):
        fptable.fp_lib_table.libs.append(
            C_kicad_fp_lib_table_file.C_fp_lib_table.C_lib(
                name="lcsc",
                type="KiCad",
                uri=uri,
                options="",
                descr="FBRK: LCSC footprints auto-downloaded",
            )
        )
        logger.warning(
            "Changed fp-lib-table to include lcsc library, need to restart pcbnew"
        )

    fptable.dumps(fplibpath)


def find_pcbnew() -> os.PathLike:
    """Figure out what to call for the pcbnew CLI."""
    if sys.platform.startswith("linux"):
        return "pcbnew"

    if sys.platform.startswith("darwin"):
        base = Path("/Applications/KiCad/")
    elif sys.platform.startswith("win"):
        base = Path(os.getenv("ProgramFiles")) / "KiCad"
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")

    if path := list(base.glob("**/pcbnew")):
        # TODO: find the best version
        return path[0]

    raise FileNotFoundError("Could not find pcbnew executable")


def open_pcb(pcb_path: os.PathLike):
    import subprocess

    pcbnew = find_pcbnew()
    subprocess.Popen([str(pcbnew), str(pcb_path)], stderr=subprocess.DEVNULL)
    # TODO: it'd be neat if we could wait until pcbnew was closed?


def apply_netlist(pcb_path: Path, netlist_path: Path, netlist_has_changed: bool = True):
    include_footprints(pcb_path)

    # Set netlist path in gui menu
    prj_path = pcb_path.with_suffix(".kicad_pro")
    if not prj_path.exists():
        project = C_kicad_project_file()
    else:
        project = C_kicad_project_file.loads(prj_path)
    project.pcbnew.last_paths.netlist = str(
        netlist_path.resolve().relative_to(pcb_path.parent.resolve(), walk_up=True)
    )
    project.dumps(prj_path)

    # Import netlist into pcb
    if not netlist_has_changed:
        return

    print("Importing netlist manually...")

    auto_mode = os.environ.get("FBRK_NETLIST_PCBNEW_AUTO", "y").lower() in [
        "y",
        "1",
    ]

    if auto_mode:
        try:
            open_pcb(pcb_path)
        except FileNotFoundError:
            print(f"PCB location: {pcb_path}")
    else:
        print(f"PCB location: {pcb_path}")

    input(
        "Load the netlist in File->Import->Netlist: Update PCB\n"
        "Then press ENTER to continue..."
    )
