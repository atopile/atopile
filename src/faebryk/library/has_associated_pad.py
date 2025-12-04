# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
from faebryk.library import _F as F


class has_associated_pad(fabll.Node):
    """
    A node that has an associated pad.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    pad_ptr_ = F.Collections.Pointer.MakeChild()

    @property
    def pad(self):
        """The pad associated with this node"""
        return self.pad_ptr_.get().deref()

    @classmethod
    def MakeChild(cls, pad: fabll._ChildField[fabll.Node]) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(pad)
        return out

    def setup(self, pad: fabll.Node) -> Self:
        from faebryk.library.has_associated_net import has_associated_net

        self.pad_ptr_.get().point(pad)

        parent = self.get_parent_with_trait(F.is_lead)[0].cast(F.Lead)
        if parent is None:
            raise ValueError("Parent is not a Lead")
        pad.get_trait(
            has_associated_net
        ).net.part_of.get()._is_interface.get().connect_to(parent.line.get())
        return self
