# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Mapping

import psutil
from more_itertools import first

import faebryk.library._F as F
from atopile.config import config
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.node import Node, NodeException
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
from faebryk.libs.util import hash_string, not_none, once

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
    lib_name: str, fppath: os.PathLike, fptable: C_kicad_fp_lib_table_file | None = None
):
    fppath = Path(fppath)

    if fptable is None:
        try:
            fptable = C_kicad_fp_lib_table_file.loads(config.build.paths.fp_lib_table)
        except FileNotFoundError:
            fptable = C_kicad_fp_lib_table_file.skeleton()

    relative = True
    try:
        fppath_rel = fppath.resolve().relative_to(
            config.build.paths.fp_lib_table.parent.resolve(), walk_up=True
        )
        # check if not going up outside the project directory
        # relative_to raises a ValueError if it has to walk up to make a relative path
        fppath.relative_to(not_none(config.project.paths.root))
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

    matching_libs = [
        lib_ for lib_ in fptable.fp_lib_table.libs if lib_.name == lib.name
    ]
    lib_is_duplicated = len(matching_libs) != 1
    lib_is_outdated = any(lib_ != lib for lib_ in matching_libs)

    if lib_is_duplicated or lib_is_outdated:
        fptable.fp_lib_table.libs = [
            lib for lib in fptable.fp_lib_table.libs if lib.name != lib_name
        ] + [lib]

        logger.warning("pcbnew restart required (updated fp-lib-table)")

    fptable.dumps(config.build.paths.fp_lib_table)

    return fptable


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


def apply_netlist(files: tuple[C_kicad_pcb_file, C_kicad_netlist_file] | None = None):
    ensure_footprint_lib("lcsc", config.project.paths.footprint_lib("lcsc"))

    set_kicad_netlist_path_in_project(
        config.build.paths.kicad_project, config.build.paths.netlist
    )

    # Import netlist into pcb
    if files:
        pcb, netlist = files
        PCB.apply_netlist(pcb, netlist, config.build.paths.fp_lib_table)
    else:
        logger.info(f"Apply netlist to {config.build.paths.layout}")
        PCB.apply_netlist_to_file(config.build.paths.layout, config.build.paths.netlist)


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


def create_footprint_library(app: Module) -> None:
    """
    Ensure all KicadFootprints have a kicad identifier (via the F.has_kicad_footprint
    trait).

    Create a footprint library for all the footprints with files and without KiCAD
    identifiers.

    Check all of the KicadFootprints have a manual identifier. Raise an error if they
    don't.
    """
    LIB_NAME = "atopile"

    # Create the library it doesn't exist
    atopile_fp_dir = config.project.paths.footprint_lib("atopile")
    atopile_fp_dir.mkdir(parents=True, exist_ok=True)
    ensure_footprint_lib(LIB_NAME, atopile_fp_dir)

    # Cache the mapping from path to identifier and the path to the new file
    path_to_fp_id: dict[Path, str] = {}
    path_map: dict[Path, Path] = {}

    def _ensure_fp(path: Path) -> tuple[str, Path]:
        """
        Ensure the footprint is in the library
        Return the identifier and the path to the new file
        """
        if path not in path_to_fp_id:
            mini_hash = hash_string(str(path))[:6]
            path_to_fp_id[path] = f"{LIB_NAME}:{path.stem}-{mini_hash}"
            path_map[path] = atopile_fp_dir / f"{path.stem}-{mini_hash}{path.suffix}"
            shutil.copy(path, path_map[path])

        return path_to_fp_id[path], path_map[path]

    for fp in app.get_children(direct_only=False, types=F.KicadFootprint):
        # has_kicad_identifier implies has_kicad_footprint, but not the other way around
        if fp.has_trait(F.has_kicad_footprint):
            # I started writing this and forgot where I was going
            # So I'm going to leave it an attempt to prompt my or someone else's ideas
            # as to what we were supposed to do here
            pass
        else:
            if has_file_t := fp.try_get_trait(F.KicadFootprint.has_file):
                # Copy the footprint to the new library with a
                # pseudo-guaranteed unique name
                path = Path(has_file_t.file).expanduser().resolve()
                lib_path, fp_path = _ensure_fp(path)
                fp.add(F.KicadFootprint.has_file(fp_path))  # Override with new path
                # Attach the newly minted identifier
                fp.add(F.KicadFootprint.has_kicad_identifier(lib_path))
            else:
                # This shouldn't happen
                # KicadFootprint should always have a file, or an identifier
                raise NodeException(
                    fp, f"{fp.__class__.__name__} has no footprint identifier or file"
                )
