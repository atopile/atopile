# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import NodeException
from faebryk.core.reference import Reference, reference
from faebryk.libs.util import not_none


class Pad(ModuleInterface):
    # FIXME: can net this become a reference instead?
    net: F.Electrical
    pcb: ModuleInterface
    interface = reference(F.Electrical)

    def attach(self, intf: F.Electrical):
        self.net.connect(intf)
        self.interface = intf
        intf.add(F.has_linked_pad_defined(self))

    @staticmethod
    def find_pad_for_intf_with_parent_that_has_footprint_unique(
        intf: ModuleInterface,
    ) -> "Pad":
        pads = Pad.find_pad_for_intf_with_parent_that_has_footprint(intf)
        if len(pads) != 1:
            raise ValueError
        return next(iter(pads))

    @staticmethod
    def find_pad_for_intf_with_parent_that_has_footprint(
        intf: ModuleInterface,
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
            if pad.net.is_connected_to(intf) is not None
        ]
        return pads

    def get_fp(self) -> F.Footprint:
        return not_none(self.get_parent_of_type(F.Footprint))
