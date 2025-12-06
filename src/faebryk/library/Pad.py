# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import TYPE_CHECKING

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none

if TYPE_CHECKING:
    from faebryk.library.has_linked_pad import has_linked_pad


class Pad(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    net = F.Electrical.MakeChild()
    pcb = fabll.NodeWithInterface.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    def attach(self, intf: F.Electrical):
        self.net.get()._is_interface.get().connect_to(intf)
        fabll.Traits.create_and_add_instance_to(node=intf, trait=has_linked_pad).setup(
            pad=self
        )

    @staticmethod
    def find_pad_for_intf_with_parent_that_has_footprint_unique(
        intf: fabll.Node,
    ) -> "Pad":
        pads = Pad.find_pad_for_intf_with_parent_that_has_footprint(intf)
        if len(pads) != 1:
            raise ValueError
        return next(iter(pads))

    @staticmethod
    def find_pad_for_intf_with_parent_that_has_footprint(
        intf: fabll.Node,
    ) -> list["Pad"]:
        # This only finds directly attached pads
        # -> misses from parents / children nodes
        # if intf.has_trait(F.has_lnked_pad):
        #     return list(intf.get_trait(F.has_lnked_pad).get_pads())

        # This is a bit slower, but finds them all
        _, footprint = F.Footprints.GenericFootprint.get_footprint_of_parent(intf)
        pads = [
            pad
            for pad in footprint.get_children(
                direct_only=True,
                types=Pad,
                required_trait=fabll.is_interface,
            )
            if pad.net.get()._is_interface.get().is_connected_to(intf)
        ]
        return pads

    def get_fp(self) -> F.Footprints.GenericFootprint:
        return not_none(self.get_parent_of_type(F.Footprints.GenericFootprint))

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
            import Pad

            pad = new Pad
            electrical_signal ~ pad.net
            """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
