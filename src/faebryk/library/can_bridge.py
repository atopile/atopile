# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class can_bridge(fabll.Node):
    is_trait = fabll.Traits.MakeEdge((fabll.ImplementsTrait.MakeChild())).put_on_type()

    in_ = F.Collections.Pointer.MakeChild()
    out_ = F.Collections.Pointer.MakeChild()

    def bridge(self, _in: fabll.Node, _out: fabll.Node):
        _in._is_interface.get().connect_to(self.get_in())
        _out._is_interface.get().connect_to(self.get_out())

    def get_in(self) -> fabll.Node:
        in_ = self.in_.get().deref()
        if in_ is None:
            raise ValueError("in is None")
        return in_

    def get_out(self) -> fabll.Node:
        out_ = self.out_.get().deref()
        if out_ is None:
            raise ValueError("out is None")
        return out_

    @classmethod
    def MakeChild(cls, in_: fabll._ChildField, out_: fabll._ChildField):
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.in_],
                [in_],
            )
        )
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.out_],
                [out_],
            )
        )
        return out

    def setup(self, in_: fabll.Node, out_: fabll.Node) -> Self:
        self.in_.get().point(in_)
        self.out_.get().point(out_)
        return self
