# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path
from typing import TYPE_CHECKING, override

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.core.reference import reference
from faebryk.core.trait import Trait
from faebryk.libs.kicad.fileformats_latest import (
    C_kicad_drc_report_file,
    C_kicad_pcb_file,
)
from faebryk.libs.kicad.fileformats_version import try_load_kicad_pcb_file
from faebryk.libs.units import to_si_str
from faebryk.libs.util import find, groupby, md_list

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer


class PCB(Node):
    def __init__(self, path: Path):
        super().__init__()

        self._path = path
        self._pcb_file: C_kicad_pcb_file | None = None
        self._transformer: "PCB_Transformer | None" = None
        self.app: Module | None = None

    def load(self):
        from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

        assert self.app is not None

        self._pcb_file = try_load_kicad_pcb_file(self._path)
        self._transformer = PCB_Transformer(
            self._pcb_file.kicad_pcb, self.app.get_graph(), self.app
        )

    @property
    def transformer(self) -> "PCB_Transformer":
        assert self._transformer is not None
        return self._transformer

    @property
    def pcb_file(self) -> C_kicad_pcb_file:
        assert self._pcb_file is not None
        return self._pcb_file

    class requires_drc_check(Trait.decless()):
        type Violation = C_kicad_drc_report_file.C_Violation

        class DrcException(F.implements_design_check.UnfulfilledCheckException):
            type Violation = PCB.requires_drc_check.Violation

            def __init__(
                self,
                pcb: "PCB",
                shorts: list[Violation],
                unconnected: list[Violation],
                units: str,
            ):
                self.shorts = shorts
                self.unconnected = unconnected
                self.units = units
                super().__init__(
                    (
                        f"{type(self).__name__} "
                        f"({len(self.shorts)} shorts, "
                        f"{len(self.unconnected)} unconnected)"
                    ),
                    nodes=[],
                )

            def pretty_violation(self, violation: Violation):
                def _convert_coord(c):
                    x, y = (to_si_str(subcoord, self.units) for subcoord in (c.x, c.y))
                    return f"({x},{y})"

                return {
                    violation.description: [
                        f"{i.description} @{_convert_coord(i.pos)}"
                        for i in violation.items
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

            def __str__(self):
                return self.pretty()

        design_check: F.implements_design_check

        @F.implements_design_check.register_post_pcb_check
        def __check_post_pcb__(self):
            from faebryk.libs.kicad.drc import run_drc as run_drc_kicad

            pcb = self.get_obj(PCB)
            assert pcb._path is not None

            drc_report = run_drc_kicad(pcb._path)

            grouped = groupby(drc_report.violations, lambda v: v.type)
            not_connected = drc_report.unconnected_items

            shorts = grouped.get(
                C_kicad_drc_report_file.C_Violation.C_Type.shorting_items, []
            )
            if shorts or not_connected:
                raise self.DrcException(
                    pcb, shorts, not_connected, drc_report.coordinate_units
                )

    # TODO use reference
    class has_pcb(Module.TraitT.decless()):
        class has_pcb_ref(F.has_reference.decless()):
            reference: "PCB" = reference()

        def __init__(self, pcb: "PCB"):
            super().__init__()
            self._pcbs = {pcb}

        def on_obj_set(self):
            obj = self.get_obj(Module)
            for pcb in self._pcbs:
                if pcb.app and pcb.app is not obj:
                    raise ValueError(
                        f"PCB {pcb._path} already has an app {pcb.app}."
                        f" Can't assign {obj}"
                    )
                pcb.app = obj
                pcb.app.add(self.has_pcb_ref(pcb))

            return super().on_obj_set()

        @override
        def handle_duplicate(self, old: "PCB.has_pcb", node: Node) -> bool:
            self._pcbs.update(old._pcbs)
            return True

        @property
        def pcbs(self) -> set["PCB"]:
            return self._pcbs

        def get_pcb_by_path(self, path: Path) -> "PCB":
            return find(self._pcbs, lambda pcb: pcb._path == path)
