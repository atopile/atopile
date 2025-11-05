# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none


class Pad(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    net = F.Electrical.MakeChild()
    pcb = fabll.GenericNodeWithInterface.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()

    # ----------------------------------------
    #                WIP
    # ----------------------------------------

    def attach(self, intf: F.Electrical):
        self.net.connect(intf)
        intf.add(F.has_linked_pad_defined(self))

    @staticmethod
    def find_pad_for_intf_with_parent_that_has_footprint_unique(
        intf: fabll.ModuleInterface,
    ) -> "Pad":
        pads = Pad.find_pad_for_intf_with_parent_that_has_footprint(intf)
        if len(pads) != 1:
            raise ValueError
        return next(iter(pads))

    @staticmethod
    def find_pad_for_intf_with_parent_that_has_footprint(
        intf: fabll.ModuleInterface,
    ) -> list["Pad"]:
        # This only finds directly attached pads
        # -> misses from parents / children nodes
        # if intf.has_trait(F.has_linked_pad):
        #     return list(intf.get_trait(F.has_linked_pad).get_pads())

        # This is a bit slower, but finds them all
        _, footprint = F.Footprint.get_footprint_of_parent(intf)
        pads = [
            pad
            for pad in footprint.get_children(direct_only=True, types=Pad)
            if pad.net.get_trait(fabll.is_interface).is_connected_to(intf)
        ]
        return pads

    def get_fp(self) -> F.Footprint:
        return not_none(self.get_parent_of_type(F.Footprint))

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import Pad

        pad = new Pad
        electrical_signal ~ pad.net
        """,
        language=F.has_usage_example.Language.ato,
    )
