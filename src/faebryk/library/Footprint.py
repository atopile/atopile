# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.core import Module, ModuleInterface, Node


class Footprint(Module):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def get_footprint_of_parent(
        intf: ModuleInterface,
    ) -> "tuple[Node, Footprint]":
        from faebryk.core.util import get_parent_with_trait
        from faebryk.library.has_footprint import has_footprint

        parent, trait = get_parent_with_trait(intf, has_footprint)
        return parent, trait.get_footprint()
