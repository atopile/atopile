# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from pathlib import Path

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.libs.app.erc import simple_erc
from faebryk.libs.kicad.fileformats_latest import C_kicad_drc_report_file
from faebryk.libs.units import to_si_str
from faebryk.libs.util import groupby, md_list

logger = logging.getLogger(__name__)


class CheckException(Exception): ...


def run_checks(app: Module, G: Graph):
    # TODO should make a Trait Trait: `implements_design_check`
    check_requires_external_usage(app, G)
    simple_erc(G)


class RequiresExternalUsageNotFulfilled(CheckException):
    def __init__(self, nodes: list[Node]):
        self.nodes = nodes
        super().__init__(
            f"Nodes requiring external usage but not used externally: "
            f"{', '.join(mif.get_full_name() for mif in nodes)}"
        )


def check_requires_external_usage(app: Module, G: Graph):
    unfulfilled = []
    for node, trait in GraphFunctions(G).nodes_with_trait(F.requires_external_usage):
        if not trait.fulfilled:
            # Don't check the app module itself
            if app is node:
                continue
            unfulfilled.append(node)
    if unfulfilled:
        raise RequiresExternalUsageNotFulfilled(unfulfilled)


def run_post_pcb_checks(app: Module, G: Graph, pcb: Path):
    run_drc(app, G, pcb)


type Violation = C_kicad_drc_report_file.C_Violation


class DrcException(CheckException):
    def __init__(
        self,
        shorts: list[Violation],
        unconnected: list[Violation],
        units: str,
    ):
        self.shorts = shorts
        self.unconnected = unconnected
        self.units = units
        super().__init__(
            f"{type(self).__name__} ("
            f"{len(self.shorts)} shorts,"
            f"{len(self.unconnected)} unconnected"
            f")"
        )

    def pretty_violation(self, violation: Violation):
        def _convert_coord(c):
            x, y = (to_si_str(subcoord, self.units) for subcoord in (c.x, c.y))
            return f"({x},{y})"

        return {
            violation.description: [
                f"{i.description} @{_convert_coord(i.pos)}" for i in violation.items
            ]
        }

    def pretty(self) -> str:
        out = ""
        if self.shorts:
            out += "\n\nShorts\n"
            out += md_list(
                [self.pretty_violation(v) for v in self.shorts],
                recursive=True,
            )
        if self.unconnected:
            out += "\n\nMissing connections\n"
            out += md_list(
                [self.pretty_violation(v) for v in self.unconnected],
                recursive=True,
            )
        return out


def run_drc(app: Module, G: Graph, pcb: Path):
    from faebryk.libs.kicad.drc import run_drc as run_drc_kicad

    drc_report = run_drc_kicad(pcb)

    grouped = groupby(drc_report.violations, lambda v: v.type)
    not_connected = drc_report.unconnected_items

    shorts = grouped.get(C_kicad_drc_report_file.C_Violation.C_Type.shorting_items, [])
    if shorts or not_connected:
        raise DrcException(shorts, not_connected, drc_report.coordinate_units)
