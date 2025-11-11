# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Self, cast

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)


class Net(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    part_of = F.Electrical.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.is_module.MakeChild()

    # ----------------------------------------
    #                WIP
    # ----------------------------------------
    def get_connected_pads(self) -> dict[F.Pad, F.Footprint]:
        return {
            pad: fp
            for mif in self.get_connected_interfaces()
            if (fp := mif.get_parent_of_type(F.Footprint)) is not None
            and (pad := mif.get_parent_of_type(F.Pad)) is not None
        }

    def get_footprints(self) -> set[F.Footprint]:
        return {
            fp
            for mif in self.get_connected_interfaces()
            if (fp := mif.get_parent_of_type(F.Footprint)) is not None
        }

    # TODO should this be here?
    def get_connected_interfaces(self) -> dict[fabll.Node, fabll.Path]:
        return self.part_of.get().get_trait(fabll.is_interface).get_connected()

    def __repr__(self) -> str:
        up = super().__repr__()
        if self.has_trait(F.has_overriden_name):
            return f"{up}'{self.get_trait(F.has_overriden_name).get_name()}'"
        else:
            return up

    @classmethod
    def MakeChild(cls, name: str) -> fabll.ChildField:
        out = fabll.ChildField(cls)
        out.add_dependant(F.has_overriden_name.MakeChild(name))
        return out

    def setup(self, name: str) -> Self:
        fabll.Node.bind_typegraph_from_instance(instance=self.instance).create_instance(
            g=self.instance.g()
        ).get_trait(F.has_overriden_name).setup(name=name)
        return self

    def setup_from_part_of_mif(self, mif: F.Electrical) -> "Net":
        """Return the Net that this "part_of" mif represents"""
        name = not_none(mif.get_trait(F.has_overriden_name).get_name())
        self = self.setup(name=name)
        return self

    def find_nets_for_mif(self, mif: F.Electrical) -> set["Net"]:
        """Return all nets that are connected to this mif"""
        return {
            net
            for net_mif in mif.get_trait(fabll.is_interface).get_connected()
            if (net := self.setup_from_part_of_mif(mif=cast(F.Electrical, net_mif)))
        }
