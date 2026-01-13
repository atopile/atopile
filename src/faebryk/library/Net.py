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
    is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    part_of = F.Electrical.MakeChild()

    # ----------------------------------------
    #                 functions
    # ----------------------------------------

    def get_members(self) -> list[fabll.Node]:
        """
        Get all interfaces directly connected to this net (O(n) where n = members).
        This returns only the direct connections, not transitive BFS.
        """
        return self.part_of.get()._is_interface.get().get_direct_connections()

    def get_connected_pads(self) -> set[F.Footprints.is_pad]:
        """
        Get all pads connected to this net.
        Uses direct connections for O(n) lookup instead of BFS.
        """
        connected_pads: set[F.Footprints.is_pad] = set()

        # Use get_members() for O(n) direct lookup instead of BFS
        for electrical in self.get_members():
            # if those electricals have a is_lead trait, we're in business
            if is_lead := electrical.try_get_trait(F.Lead.is_lead):
                # and if that is_lead has associated pads...
                if has_associated_pads := is_lead.try_get_trait(
                    F.Lead.has_associated_pads
                ):
                    # add those pads to the set!
                    for is_pad in has_associated_pads.get_pads():
                        connected_pads.add(is_pad)

        return connected_pads

    def get_name(self) -> str | None:
        if has_net_name := self.try_get_trait(F.has_net_name):
            return has_net_name.get_name()
        return None

    def get_connected_interfaces(self) -> list[F.Electrical]:
        """Get all electrical interfaces directly connected to this net."""
        return [e.cast(F.Electrical) for e in self.get_members()]

    # ----------------------------------------
    #                WIP
    # ----------------------------------------

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

    def setup(self, net_name: str) -> "Net":
        fabll.Traits.create_and_add_instance_to(
            self.part_of.get(), F.has_net_name
        ).setup(name=net_name)
        return self
