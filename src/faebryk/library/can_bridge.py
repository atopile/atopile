# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer


class can_bridge(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()
    in_ = fabll.ChildField(fabll.Node)
    out_ = fabll.ChildField(fabll.Node)

    def bridge(self, _in: fabll.Node, out: fabll.Node):
        _in.get_trait(fabll.is_interface).connect_to(self.get_in())
        out.get_trait(fabll.is_interface).connect_to(self.get_out())

    def get_in(self) -> fabll.Node:
        in_ = EdgePointer.get_referenced_node_from_node(node=self.in_.get().instance)
        if in_ is None:
            raise ValueError("in is None")
        return fabll.Node.bind_instance(in_)

    def get_out(self) -> fabll.Node:
        out = EdgePointer.get_referenced_node_from_node(node=self.out_.get().instance)
        if out is None:
            raise ValueError("out is None")
        return fabll.Node.bind_instance(out)

    @classmethod
    def MakeChild(cls, in_: fabll.ChildField, out_: fabll.ChildField):
        out = fabll.ChildField(cls)
        out.add_dependant(
            fabll.EdgeField(
                [out, cls.in_],
                [in_],
                edge=EdgePointer.build(identifier="in", order=None),
            )
        )
        out.add_dependant(
            fabll.EdgeField(
                [out, cls.out_],
                [out_],
                edge=EdgePointer.build(identifier="out", order=None),
            )
        )
        return out
