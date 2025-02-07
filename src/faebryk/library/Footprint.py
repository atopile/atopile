# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from abc import abstractmethod
from typing import TYPE_CHECKING

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.core.trait import Trait

if TYPE_CHECKING:
    from faebryk.library._F import Pad


class Footprint(Module):
    class TraitT(Trait): ...

    class has_equal_pins(TraitT.decless()):
        """Footprint has an equal number of landing pads as logical pads"""

        def get_pin_map(self):
            from faebryk.library._F import Pad

            return {
                p: str(i + 1)
                for i, p in enumerate(
                    self.obj.get_children(direct_only=True, types=Pad)
                )
            }

    class can_attach_via_pinmap(TraitT):
        @abstractmethod
        def attach(self, pinmap: dict[str, F.Electrical | None]): ...

    class can_attach_via_pinmap_equal(can_attach_via_pinmap.impl()):
        def attach(self, pinmap: dict[str, F.Electrical]):
            pin_list = {
                v: k
                for k, v in self.obj.get_trait(Footprint.has_equal_pins)
                .get_pin_map()
                .items()
            }
            for no, intf in pinmap.items():
                pin_list[no].attach(intf)

    class can_attach_via_pinmap_pinlist(can_attach_via_pinmap.impl()):
        def __init__(self, pin_list: dict[str, "Pad"]) -> None:
            super().__init__()
            self.pin_list = pin_list

        def attach(self, pinmap: dict[str, F.Electrical | None]):
            for no, intf in pinmap.items():
                if intf is None:
                    continue
                assert (
                    no in self.pin_list
                ), f"Pin {no} not in pin list: {self.pin_list.keys()}"
                self.pin_list[no].attach(intf)

    @staticmethod
    def get_footprint_of_parent(
        intf: ModuleInterface,
    ) -> "tuple[Node, Footprint]":
        parent, trait = intf.get_parent_with_trait(F.has_footprint)
        return parent, trait.get_footprint()
