# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class can_bridge_by_name(fabll.Node):
    """
    Only keeping for ato v1 compatibility.
    """

    is_trait = fabll.Traits.MakeEdge((fabll.ImplementsTrait.MakeChild())).put_on_type()

    # TODO: Forward this trait to parent
    _can_bridge = fabll.Traits.MakeEdge(fabll._ChildField(F.can_bridge))

    def setup(self, input_name: str, output_name: str) -> Self:
        input_node_list = self.get_parent_force()[0].get_children(
            False, types=fabll.Node, f_filter=lambda x: x.get_name() == input_name
        )
        if len(input_node_list) != 1:
            raise ValueError(f"Expected 1 input node, got {len(input_node_list)}")
        output_node_list = self.get_parent_force()[0].get_children(
            False, types=fabll.Node, f_filter=lambda x: x.get_name() == output_name
        )
        if len(output_node_list) != 1:
            raise ValueError(f"Expected 1 output node, got {len(output_node_list)}")

        self._can_bridge.get().setup(input_node_list[0], output_node_list[0])
        return self
