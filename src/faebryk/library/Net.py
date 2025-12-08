# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from typing_extensions import deprecated

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class Net(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    part_of = F.Electrical.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # ----------------------------------------
    #                WIP
    # ----------------------------------------
    def get_connected_pads(self) -> dict[F.Pad, F.Footprints.GenericFootprint]:
        return {
            pad: fp
            for mif in self.part_of.get()._is_interface.get().get_connected()
            if (fp := mif.get_parent_of_type(F.Footprints.GenericFootprint)) is not None
            and (pad := mif.get_parent_of_type(F.Pad)) is not None
        }

    def get_footprints(self) -> set[F.Footprints.GenericFootprint]:
        return {
            fp
            for mif in self.part_of.get()._is_interface.get().get_connected()
            if (fp := mif.get_parent_of_type(F.Footprints.GenericFootprint)) is not None
        }

    def get_name(self) -> str:
        return self.get_trait(F.has_net_name).get_name()

    def __repr__(self) -> str:
        up = super().__repr__()
        if self.has_trait(F.has_net_name):
            return f"{up}'{self.get_trait(F.has_net_name).get_name()}'"
        else:
            return up

    @staticmethod
    @deprecated("Use is_interface.get_connected instead")
    def find_nets_for_mif(mif: F.Electrical) -> set["Net"]:
        """Return all nets that are connected to this mif"""
        return {
            net
            for net_mif in mif._is_interface.get().get_connected()
            if (net := mif.get_parent_of_type(Net)) is not None
        }
