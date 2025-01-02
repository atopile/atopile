# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

import psutil
from more_itertools import first

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.exporters.pcb.kicad.pcb import PCB
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import apply_route_in_pcb
from faebryk.libs.exceptions import UserResourceException, downgrade
from faebryk.libs.kicad.fileformats import (
    C_kicad_fp_lib_table_file,
    C_kicad_netlist_file,
    C_kicad_pcb_file,
    C_kicad_project_file,
)
from faebryk.libs.util import not_none, once

if TYPE_CHECKING:
    from atopile.config import BuildPaths

logger = logging.getLogger(__name__)


def apply_layouts(app: Module):
    if not app.has_trait(F.has_pcb_position):
        app.add(
            F.has_pcb_position_defined(
                F.has_pcb_position.Point((0, 0, 0, F.has_pcb_position.layer_type.NONE))
            )
        )

    for level in app.get_tree(types=Node).iter_by_depth():
        for n in level:
            if n.has_trait(F.has_pcb_layout):
                n.get_trait(F.has_pcb_layout).apply()


def apply_routing(app: Module, transformer: PCB_Transformer):
    strategies: list[tuple[F.has_pcb_routing_strategy, int]] = []

    for i, level in enumerate(app.get_tree(types=Node).iter_by_depth()):
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


def ensure_footprint_lib(
    build_paths: "BuildPaths",
    lib_name: str,
    fppath: os.PathLike,
    fptable: C_kicad_fp_lib_table_file | None = None,
):
    fppath = Path(fppath)

    if fptable is None:
        try:
            fptable = C_kicad_fp_lib_table_file.loads(
                path_or_string_or_data=build_paths.fp_lib_table
            )
        except FileNotFoundError:
            fptable = C_kicad_fp_lib_table_file.skeleton()

    relative = True
    try:
        fppath_rel = fppath.resolve().relative_to(
            build_paths.layout.parent.resolve(), walk_up=True
        )
        # check if not going up outside the project directory
        # relative_to raises a ValueError if it has to walk up to make a relative path
        fppath.relative_to(not_none(build_paths.root))
    except ValueError:
        relative = False
        with downgrade(UserResourceException):
            raise UserResourceException(
                f"Footprint path {fppath} is outside the project directory."
                "This is unstable behavior and may be deprecated in the future."
            )
    else:
        fppath = fppath_rel

    uri = str(fppath)
    if relative:
        assert not uri.startswith("/")
        assert not uri.startswith("${KIPRJMOD}")
        uri = "${KIPRJMOD}/" + uri

    lib = C_kicad_fp_lib_table_file.C_fp_lib_table.C_lib(
        name=lib_name,
        type="KiCad",
        uri=uri,
        options="",
        descr=f"atopile: {lib_name} footprints",
    )

    lib_libs = [lib for lib in fptable.fp_lib_table.libs if lib.name == lib_name]
    table_has_one_lib = len(lib_libs) == 1
    lib_table_outdated = any(lib != lib for lib in lib_libs)

    if not table_has_one_lib or lib_table_outdated:
        fptable.fp_lib_table.libs = [
            lib for lib in fptable.fp_lib_table.libs if lib.name != lib_name
        ] + [lib]

        logger.warning("pcbnew restart required (updated fp-lib-table)")

    fptable.dumps(build_paths.fp_lib_table)

    return fptable


def include_footprints(build_paths: "BuildPaths"):
    ensure_footprint_lib(
        build_paths, "lcsc", build_paths.component_lib / "footprints" / "lcsc.pretty"
    )


@once
def find_pcbnew() -> os.PathLike:
    """Figure out what to call for the pcbnew CLI."""
    if sys.platform.startswith("linux"):
        return Path("pcbnew")

    if sys.platform.startswith("darwin"):
        base = Path("/Applications/KiCad/")
    elif sys.platform.startswith("win"):
        base = Path(not_none(os.getenv("ProgramFiles"))) / "KiCad"
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")

    if path := list(base.glob("**/pcbnew")):
        # TODO: find the best version
        return path[0]

    raise FileNotFoundError("Could not find pcbnew executable")


def open_pcb(pcb_path: os.PathLike):
    import subprocess

    pcbnew = find_pcbnew()

    # Check if pcbnew is already running with this pcb
    for process in psutil.process_iter(["name", "cmdline"]):
        if process.info["name"] and "pcbnew" in process.info["name"].lower():
            if process.info["cmdline"] and str(pcb_path) in process.info["cmdline"]:
                raise RuntimeError(f"PCBnew is already running with {pcb_path}")

    subprocess.Popen([str(pcbnew), str(pcb_path)], stderr=subprocess.DEVNULL)


def set_kicad_netlist_path_in_project(project_path: Path, netlist_path: Path):
    """
    Set netlist path in gui menu
    """
    if not project_path.exists():
        project = C_kicad_project_file()
    else:
        project = C_kicad_project_file.loads(project_path)
    project.pcbnew.last_paths.netlist = str(
        netlist_path.resolve().relative_to(project_path.parent.resolve(), walk_up=True)
    )
    project.dumps(project_path)


def apply_netlist(
    build_paths: "BuildPaths",
    files: tuple[C_kicad_pcb_file, C_kicad_netlist_file] | None = None,
):
    include_footprints(build_paths)

    set_kicad_netlist_path_in_project(build_paths.kicad_project, build_paths.netlist)

    # Import netlist into pcb
    if files:
        pcb, netlist = files
        PCB.apply_netlist(pcb, netlist, build_paths.layout.parent / "fp-lib-table")
    else:
        logger.info(f"Apply netlist to {build_paths.layout}")
        PCB.apply_netlist_to_file(build_paths.layout, build_paths.netlist)


def load_nets(
    graph: Graph, attach: bool = False, match_threshold: float = 0.8
) -> dict[F.Net, str]:
    """
    Load nets from attached footprints and attach them to the nodes.
    """

    if match_threshold < 0.5:
        # This is because we rely on being >50% sure to ensure we're the most
        # likely match.
        raise ValueError("match_threshold must be at least 0.5")

    known_nets: dict[F.Net, str] = {}
    for net in GraphFunctions(graph).nodes_of_type(F.Net):
        total_pads = 0
        net_candidates: Mapping[str, int] = defaultdict(int)

        for ato_pad, ato_fp in net.get_fps().items():
            if pcb_pad_t := ato_pad.try_get_trait(PCB_Transformer.has_linked_kicad_pad):
                pcb_fp, pcb_pads = pcb_pad_t.get_pad()
                net_names = set(
                    pcb_pad.net.name if pcb_pad.net is not None else None
                    for pcb_pad in pcb_pads
                )
                if len(net_names) == 1 and (net_name := first(net_names)) is not None:
                    net_candidates[net_name] += 1
            total_pads += 1

        if net_candidates:
            best_net = max(net_candidates, key=lambda x: net_candidates[x])
            if best_net and net_candidates[best_net] > total_pads * match_threshold:
                known_nets[net] = best_net

    if attach:
        for net, name in known_nets.items():
            if not net.has_trait(F.has_overriden_name):
                net.add(F.has_overriden_name_defined(name))

    return known_nets
