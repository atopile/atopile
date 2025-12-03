# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
from faebryk.library import _F as F


class has_associated_net(fabll.Node):
    """
    Link between pad-node and net. Added during build process.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    net_ptr_ = F.Collections.Pointer.MakeChild()

    @property
    def net(self) -> "F.Net":
        """Return the net associated with this node"""
        return self.net_ptr_.get().deref().cast(F.Net)

    @classmethod
    def MakeChild(cls, net: "fabll._ChildField[F.Net]") -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(net)
        return out
