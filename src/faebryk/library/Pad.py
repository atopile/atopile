# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.core import ModuleInterface
from faebryk.core.util import get_parent_of_type
from faebryk.library.Electrical import Electrical
from faebryk.library.Footprint import Footprint


class Pad(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class _IFS(super().IFS()):
            net = Electrical()
            pcb = ModuleInterface()

        self.IFs = _IFS(self)

    def attach(self, intf: Electrical):
        from faebryk.library.has_linked_pad_defined import has_linked_pad_defined

        self.IFs.net.connect(intf)
        intf.add_trait(has_linked_pad_defined(self))

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
        from faebryk.library.has_linked_pad import has_linked_pad

        # This only finds directly attached pads
        # -> misses from parents / children nodes
        if intf.has_trait(has_linked_pad):
            return [intf.get_trait(has_linked_pad).get_pad()]

        # This is a bit slower, but finds them all
        _, footprint = Footprint.get_footprint_of_parent(intf)
        pads = [
            pad
            for pad in footprint.IFs.get_all()
            if isinstance(pad, Pad) and pad.IFs.net.is_connected_to(intf) is not None
        ]
        return pads

    def get_fp(self) -> Footprint:
        fp = get_parent_of_type(self, Footprint)
        assert fp
        return fp
