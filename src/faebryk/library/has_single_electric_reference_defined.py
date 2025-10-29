# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING

import faebryk.core.node as fabll

# import faebryk.library._F as F
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.libs.util import not_none

# if TYPE_CHECKING:
from faebryk.library.ElectricPower import ElectricPower


class has_single_electric_reference_defined(fabll.Node):
    # reference = fabll.ChildField(ElectricPower)

    @classmethod
    def MakeChild(cls, reference: fabll.ChildField[ElectricPower]):
        out = fabll.ChildField(cls)
        field = fabll.EdgeField(
            [out],
            [reference],
            edge=EdgePointer.build(identifier="reference", order=None),
        )
        out.add_dependant(field)
        return out

    def get_reference(self) -> "ElectricPower":
        reference_node = not_none(
            EdgePointer.get_pointed_node_by_identifier(
                identifier="reference",
                bound_node=self.instance,
            )
        )
        if not isinstance(reference_node, ElectricPower):
            raise TypeError(
                f"has_single_electric_reference_defined can only be used on "
                f"ElectricPower, got {reference_node}"
            )
        return reference_node
