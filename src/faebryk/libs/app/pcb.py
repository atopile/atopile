# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import sys
from pathlib import Path

import psutil

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import apply_route_in_pcb
from faebryk.libs.exceptions import UserResourceException, downgrade
from faebryk.libs.kicad.fileformats_latest import (
    C_kicad_project_file,
)
from faebryk.libs.util import (
    cast_assert,
    duplicates,
    groupby,
    md_list,
    not_none,
    once,
    remove_venv_from_env,
)

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

    subprocess.Popen(
        [str(pcbnew), str(pcb_path)],
        env=remove_venv_from_env(),
        stderr=subprocess.DEVNULL,
    )


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

    net_names: dict[F.Net, str] = {
        cast_assert(F.Net, net): not_none(pcb_net_t.get_net().name)
        for net, pcb_net_t in GraphFunctions(graph).nodes_with_trait(
            PCB_Transformer.has_linked_kicad_net
        )
    }

    if dups := duplicates(net_names.values(), lambda x: x):
        counts_by_net = [f"{k} (x{len(v)})" for k, v in dups.items()]
        with downgrade(UserResourceException, raise_anyway=raise_duplicates):
            # TODO: origin information
            raise UserResourceException(
                f"Multiple nets are named the same:\n{md_list(counts_by_net)}"
            )

    for net, name in net_names.items():
        net.add(F.has_overriden_name_defined(name))


def check_net_names(graph: Graph):
    """Raise an error if any nets have the same name."""
    gf = GraphFunctions(graph)
    nets = gf.nodes_of_type(F.Net)

    net_name_collisions = {
        k: v
        for k, v in groupby(
            nets, lambda n: n.get_trait(F.has_overriden_name).get_name()
        ).items()
        if len(v) > 1
    }
    if net_name_collisions:
        raise UserResourceException(f"Net name collision: {net_name_collisions}")
