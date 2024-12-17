# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.exporters.pcb.kicad.pcb import _get_footprint
from faebryk.libs.library import L
from faebryk.libs.util import times


class KicadFootprint(F.Footprint):
    def __init__(self, kicad_identifier: str, pin_names: list[str]) -> None:
        super().__init__()

        unique_pin_names = sorted(set(pin_names))
        self.pin_names_sorted = list(enumerate(unique_pin_names))
        self.kicad_identifier = kicad_identifier

    @classmethod
    def with_simple_names(cls, kicad_identifier: str, pin_cnt: int):
        return cls(kicad_identifier, [str(i + 1) for i in range(pin_cnt)])

    @classmethod
    def from_library(cls, kicad_identifier: str):
        # TODO this is ugly
        try:
            from atopile.config import get_build_context

            ctx = get_build_context()
            fp_lib_path = ctx.paths.layout.parent / "fp-lib-table"
        except Exception:
            fp_lib_path = None
        fp = _get_footprint(kicad_identifier, fp_lib_path)
        return cls(kicad_identifier, pin_names=[p.name for p in fp.pads])

    @L.rt_field
    def pins(self):
        return times(len(self.pin_names_sorted), F.Pad)

    @L.rt_field
    def attach_via_pinmap(self):
        return F.can_attach_via_pinmap_pinlist(
            {pin_name: self.pins[i] for i, pin_name in self.pin_names_sorted}
        )

    @L.rt_field
    def kicad_footprint(self):
        return F.has_kicad_manual_footprint(
            self.kicad_identifier,
            {self.pins[i]: pin_name for i, pin_name in self.pin_names_sorted},
        )
