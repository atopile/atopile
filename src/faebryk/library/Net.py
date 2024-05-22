# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Footprint, Module
from faebryk.core.util import get_connected_mifs, get_parent_of_type
from faebryk.library.Electrical import Electrical
from faebryk.library.has_overriden_name import has_overriden_name
from faebryk.library.has_overriden_name_defined import has_overriden_name_defined

logger = logging.getLogger(__name__)


class Net(Module):
    def __init__(self) -> None:
        super().__init__()

        class _IFs(super().IFS()):
            part_of = Electrical()

        self.IFs = _IFs(self)

        class _(has_overriden_name.impl()):
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
                        + t.get_pin_name(mif)
                        for mif, fp in self.get_fps().items()
                        if fp.has_trait(can_represent_kicad_footprint)
                    )
                )

                # kicad can't handle long net names
                if len(name) > 255:
                    name = name[:200] + "..." + name[-52:]

                return name

        self.add_trait(_())

    def get_fps(self):
        return {
            mif: fp
            for mif in self.get_connected_interfaces()
            if (fp := get_parent_of_type(mif, Footprint)) is not None
        }

    # TODO should this be here?
    def get_connected_interfaces(self):
        return {
            mif
            for mif in get_connected_mifs(self.IFs.part_of.GIFs.connected)
            if isinstance(mif, type(self.IFs.part_of))
        }

    def __repr__(self) -> str:
        up = super().__repr__()
        if self.has_trait(has_overriden_name):
            return f"{up}'{self.get_trait(has_overriden_name).get_name()}'"
        else:
            return up

    @classmethod
    def with_name(cls, name: str) -> "Net":
        n = cls()
        n.add_trait(has_overriden_name_defined(name))
        return n
