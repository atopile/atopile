# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class Net(Module):
    part_of: F.Electrical

    @L.rt_field
    def overriden_name(self):
        class _(F.has_overriden_name.impl()):
            def get_name(_self):
                from faebryk.exporters.netlist.graph import (
                    can_represent_kicad_footprint,
                )

                name = "-".join(
                    sorted(
                        (
                            t := fp.get_trait(can_represent_kicad_footprint)
                        ).get_name_and_value()[0]
                        + "-"
                        + t.get_pin_name(pad)
                        for pad, fp in self.get_fps().items()
                        if fp.has_trait(can_represent_kicad_footprint)
                    )
                )

                # kicad can't handle long net names
                if len(name) > 255:
                    name = name[:200] + "..." + name[-52:]

                return name

        return _()

    def get_fps(self):
        return {
            pad: fp
            for mif in self.get_connected_interfaces()
            if (fp := mif.get_parent_of_type(F.Footprint)) is not None
            and (pad := mif.get_parent_of_type(F.Pad)) is not None
        }

    # TODO should this be here?
    def get_connected_interfaces(self):
        return {
            mif
            for mif in self.part_of.get_connected()
            if isinstance(mif, type(self.part_of))
        }

    def __repr__(self) -> str:
        up = super().__repr__()
        if self.has_trait(F.has_overriden_name):
            return f"{up}'{self.get_trait(F.has_overriden_name).get_name()}'"
        else:
            return up

    @classmethod
    def with_name(cls, name: str) -> "Net":
        n = cls()
        n.add(F.has_overriden_name_defined(name))
        return n
