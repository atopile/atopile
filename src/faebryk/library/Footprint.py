# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll


class Footprint(fabll.Node):
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    @staticmethod
    def get_footprint_of_parent(
        intf: fabll.Node,
    ) -> "tuple[fabll.Node, Footprint]":
        from faebryk.library._F import has_footprint

        parent, trait = intf.get_parent_with_trait(has_footprint)
        return parent, trait.get_footprint()
