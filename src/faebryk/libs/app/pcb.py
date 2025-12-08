# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
from pathlib import Path

import psutil

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.exceptions import UserResourceException, downgrade
from faebryk.libs.kicad.fileformats import (
    C_kicad_project_file,
)
from faebryk.libs.kicad.paths import find_pcbnew
from faebryk.libs.util import (
    cast_assert,
    duplicates,
    groupby,
    md_list,
    not_none,
    remove_venv_from_env,
)

logger = logging.getLogger(__name__)


def open_pcb(pcb_path: os.PathLike):
    import subprocess

    pcbnew = find_pcbnew()

    # Check if pcbnew is already running with this pcb
    for process in psutil.process_iter(["name", "cmdline"]):
        if process.info["name"] and "pcbnew" in process.info["name"].lower():
            if process.info["cmdline"] and str(pcb_path) in process.info["cmdline"]:
                raise RuntimeError(f"PCBnew is already running with {pcb_path}")

    # remove python venvs so kicad uses system python
    clean_env = remove_venv_from_env()
    # leave cwd (so direnv doesn't trigger)
    cwd = pcbnew.parent

    subprocess.Popen(
        [str(pcbnew), str(pcb_path)],
        env=clean_env,
        cwd=cwd,
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


# def load_net_names(tg: fbrk.TypeGraph, raise_duplicates: bool = True) -> set[F.Net]:
#     """
#     Load nets from attached footprints and attach them to the nodes.
#     """

#     net_names: dict[F.Net, str] = {
#         cast_assert(F.Net, net_t.get_net().name): not_none(net_t.get_net().name)
#         for net_t in F.PCBTransformer.has_linked_kicad_net.bind_typegraph(
#             tg
#         ).get_instances()
#     }

#     if dups := duplicates(net_names.values(), lambda x: x):
#         counts_by_net = [f"{k} (x{len(v)})" for k, v in dups.items()]
#         with downgrade(UserResourceException, raise_anyway=raise_duplicates):
#             # TODO: origin information
#             raise UserResourceException(
#                 f"Multiple nets are named the same:\n{md_list(counts_by_net)}"
#             )

#     for net, name in net_names.items():
#         fabll.Traits.create_and_add_instance_to(net, F.has_net_name).setup(name)

#     return set(net_names.keys())


# def check_net_names(tg: fbrk.TypeGraph):
#     """Raise an error if any nets have the same name."""
#     nets = F.Net.bind_typegraph(tg).get_instances()

#     named_nets = {n for n in nets if n.has_trait(F.has_net_name)}
#     net_name_collisions = {
#         k: v
#         for k, v in groupby(
#             named_nets, lambda n: n.get_trait(F.has_net_name).get_name()
#         ).items()
#         if len(v) > 1
#     }
#     if net_name_collisions:
#         raise UserResourceException(f"Net name collision: {net_name_collisions}")
