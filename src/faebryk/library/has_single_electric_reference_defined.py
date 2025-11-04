# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none


class has_single_electric_reference_defined(fabll.Node):
    reference_ptr = F.Collections.Pointer.MakeChild()

    @classmethod
    def MakeChild(cls, reference: fabll.ChildField):
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Collections.Pointer.EdgeField([out, cls.reference_ptr], [reference])
        )
        return out

    def get_reference(self):
        from faebryk.library.ElectricPower import ElectricPower

        reference_node = self.reference_ptr.get().deref()
        if not (reference_node.isinstance(ElectricPower)):
            raise TypeError(
                f"has_single_electric_reference_defined can only be used on "
                f"ElectricPower, got {reference_node}"
            )
        return reference_node  # type: ignore
