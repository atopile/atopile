# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import psutil

import faebryk.library._F as F
from faebryk.core.graph import Graph
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import apply_route_in_pcb
from faebryk.libs.app.kicad_netlist import write_netlist
from faebryk.libs.app.parameters import resolve_dynamic_parameters
from faebryk.libs.exceptions import UserResourceException, downgrade
from faebryk.libs.kicad.fileformats import (
    C_kicad_fp_lib_table_file,
    C_kicad_pcb_file,
    C_kicad_project_file,
)
from faebryk.libs.util import ConfigFlag

if TYPE_CHECKING:
    from atopile.config import BuildPaths

logger = logging.getLogger(__name__)

PCBNEW_AUTO = ConfigFlag(
    "PCBNEW_AUTO",
    default=False,
    descr="Automatically open pcbnew when applying netlist",
)


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


def apply_design(
    build_paths: "BuildPaths",
    app: Module,
    G: Graph,
    transform: Callable[[PCB_Transformer], Any] | None = None,
):
    resolve_dynamic_parameters(G)

    logger.info(f"Writing netlist to {build_paths.netlist}")
    changed = write_netlist(G, build_paths.netlist, use_kicad_designators=True)
    apply_netlist(build_paths, changed)

    logger.info("Load PCB")
    pcb = C_kicad_pcb_file.loads(build_paths.layout)

    transformer = PCB_Transformer(pcb.kicad_pcb, G, app)

    logger.info("Transform PCB")
    if transform:
        transform(transformer)

    # set layout
    apply_layouts(app)
    transformer.move_footprints()
    apply_routing(app, transformer)

    logger.info(f"Writing pcbfile {build_paths.layout}")
    pcb.dumps(build_paths.layout)

    print("Reopen PCB in kicad")
    if PCBNEW_AUTO:
        try:
            open_pcb(build_paths.layout)
        except FileNotFoundError:
            print(f"PCB location: {build_paths.layout}")
        except RuntimeError as e:
            print(f"{e.args[0]}\nReload pcb manually by pressing Ctrl+O; Enter")
    else:
        print(f"PCB location: {build_paths.layout}")


def include_footprints(build_paths: "BuildPaths"):
    if build_paths.fp_lib_table.exists():
        fptable = C_kicad_fp_lib_table_file.loads(
            path_or_string_or_data=build_paths.fp_lib_table
        )
    else:
        fptable = C_kicad_fp_lib_table_file(
            C_kicad_fp_lib_table_file.C_fp_lib_table(version=7, libs=[])
        )

    fppath = build_paths.component_lib / "footprints" / "lcsc.pretty"
    relative = True
    try:
        fppath_rel = fppath.resolve().relative_to(
            build_paths.layout.parent.resolve(), walk_up=True
        )
        # check if not going up outside the project directory
        # relative_to raises a ValueError if it has to walk up to make a relative path
        fppath.relative_to(build_paths.root)
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

    lcsc_lib = C_kicad_fp_lib_table_file.C_fp_lib_table.C_lib(
        name="lcsc",
        type="KiCad",
        uri=uri,
        options="",
        descr="atopile: project LCSC footprints",
    )

    lcsc_libs = [lib for lib in fptable.fp_lib_table.libs if lib.name == "lcsc"]
    table_has_one_lcsc = len(lcsc_libs) == 1
    lcsc_table_outdated = any(lib != lcsc_lib for lib in lcsc_libs)

    if not table_has_one_lcsc or lcsc_table_outdated:
        fptable.fp_lib_table.libs = [
            lib for lib in fptable.fp_lib_table.libs if lib.name != "lcsc"
        ] + [lcsc_lib]

        logger.warning("pcbnew restart required (updated fp-lib-table)")

    fptable.dumps(build_paths.fp_lib_table)


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

    # Check if pcbnew is already running with this pcb
    for process in psutil.process_iter(["name", "cmdline"]):
        if process.info["name"] and "pcbnew" in process.info["name"].lower():
            if process.info["cmdline"] and str(pcb_path) in process.info["cmdline"]:
                raise RuntimeError(f"PCBnew is already running with {pcb_path}")

    subprocess.Popen([str(pcbnew), str(pcb_path)], stderr=subprocess.DEVNULL)


def apply_netlist(build_paths: "BuildPaths", netlist_has_changed: bool = True):
    from faebryk.exporters.pcb.kicad.pcb import PCB

    include_footprints(build_paths)

    # Set netlist path in gui menu
    if not build_paths.kicad_project.exists():
        project = C_kicad_project_file()
    else:
        project = C_kicad_project_file.loads(build_paths.kicad_project)
    project.pcbnew.last_paths.netlist = str(
        build_paths.netlist.resolve().relative_to(
            build_paths.layout.parent.resolve(), walk_up=True
        )
    )
    project.dumps(build_paths.kicad_project)

    # Import netlist into pcb
    logger.info(f"Apply netlist to {build_paths.layout}")
    PCB.apply_netlist(build_paths.layout, build_paths.netlist)
