# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.trait import Trait


class Footprint(fabll.Module):
    class TraitT(Trait): ...

    @staticmethod
    def get_footprint_of_parent(
        intf: fabll.ModuleInterface,
    ) -> "tuple[fabll.Node, Footprint]":
        parent, trait = intf.get_parent_with_trait(F.has_footprint)
        return parent, trait.get_footprint()
