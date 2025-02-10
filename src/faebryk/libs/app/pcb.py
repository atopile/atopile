# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import shutil
import sys
from pathlib import Path

import psutil

import faebryk.library._F as F
from atopile.config import config
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.node import Node, NodeException
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import apply_route_in_pcb
from faebryk.libs.exceptions import UserResourceException, downgrade
from faebryk.libs.kicad.fileformats import (
    C_kicad_fp_lib_table_file,
    C_kicad_project_file,
)
from faebryk.libs.util import cast_assert, duplicates, hash_string, not_none, once

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


def load_net_names(graph: Graph, raise_duplicates: bool = True) -> None:
    """
    Load nets from attached footprints and attach them to the nodes.
    """

    gf = GraphFunctions(graph)
    net_names: dict[F.Net, str] = {
        cast_assert(F.Net, net): pcb_net_t.get_net().name
        for net, pcb_net_t in gf.nodes_with_trait(PCB_Transformer.has_linked_kicad_net)
    }

    if dups := duplicates(net_names.values(), lambda x: x):
        with downgrade(UserResourceException, raise_anyway=raise_duplicates):
            raise UserResourceException(f"Multiple nets are named the same: {dups}")

    for net, name in net_names.items():
        net.add(F.has_overriden_name_defined(name))


def create_footprint_library(app: Module) -> None:
    """
    Ensure all KicadFootprints have a kicad identifier (via the F.has_kicad_footprint
    trait).

    Create a footprint library for all the footprints with files and without KiCAD
    identifiers.

    Check all of the KicadFootprints have a manual identifier. Raise an error if they
    don't.
    """
    from atopile.packages import KNOWN_PACKAGES_TO_FOOTPRINT

    package_fp_paths = set(KNOWN_PACKAGES_TO_FOOTPRINT.values())

    LIB_NAME = "atopile"

    # Create the library it doesn't exist
    atopile_fp_dir = config.project.paths.get_footprint_lib("atopile")
    atopile_fp_dir.mkdir(parents=True, exist_ok=True)
    ensure_footprint_lib(LIB_NAME, atopile_fp_dir)

    # Cache the mapping from path to identifier and the path to the new file
    path_map: dict[Path, tuple[str, Path]] = {}

    for fp in app.get_children(direct_only=False, types=F.KicadFootprint):
        # has_kicad_identifier implies has_kicad_footprint, but not the other way around
        if fp.has_trait(F.has_kicad_footprint):
            # I started writing this and forgot where I was going
            # So I'm going to leave it an attempt to prompt my or someone else's ideas
            # as to what we were supposed to do here
            pass
        else:
            if has_file_t := fp.try_get_trait(F.KicadFootprint.has_file):
                path = has_file_t.file
                # We priverliage packages and assume this is what's dribing
                if path in package_fp_paths:
                    if path in path_map:
                        id_, new_path = path_map[path]
                    else:
                        id_ = f"{LIB_NAME}:{path.stem}"
                        new_path = atopile_fp_dir / path.name
                        shutil.copy(path, new_path)
                        path_map[path] = (id_, new_path)

                else:
                    try:
                        prj_rel_path = path.relative_to(config.project.paths.root)

                    # Raised when the file isn't relative to the project directory
                    except ValueError as ex:
                        raise UserResourceException(
                            f"Footprint file {path} is outside the project"
                            " directory. Footprint files must be in the project"
                            " directory.",
                            markdown=False,
                        ) from ex

                    # Copy the footprint to the new library with a
                    # pseudo-guaranteed unique name
                    if prj_rel_path in path_map:
                        id_, new_path = path_map[prj_rel_path]
                    else:
                        mini_hash = hash_string(str(prj_rel_path))[:6]
                        id_ = f"{LIB_NAME}:{prj_rel_path.stem}-{mini_hash}"
                        new_path = (
                            atopile_fp_dir
                            / f"{prj_rel_path.stem}-{mini_hash}{prj_rel_path.suffix}"
                        )
                        shutil.copy(path, new_path)
                        path_map[prj_rel_path] = (id_, new_path)

                fp.add(F.KicadFootprint.has_file(new_path))  # Override with new path
                # Attach the newly minted identifier
                fp.add(F.KicadFootprint.has_kicad_identifier(id_))
            else:
                # This shouldn't happen
                # KicadFootprint should always have a file, or an identifier
                raise NodeException(
                    fp, f"{fp.__class__.__name__} has no footprint identifier or file"
                )
