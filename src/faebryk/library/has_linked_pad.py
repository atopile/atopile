# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_linked_pad(fabll.Node):
    _is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()
    pad_ptr_ = F.Collections.Pointer.MakeChild()

    def get_pads(self) -> set["F.Pad"]:
        return self.pad_ptr_.get().deref()  # type: ignore

    # TODO: Implement this
    # def handle_duplicate(self, old: fabll.Node, node: fabll.Node) -> bool:
    #     raise NotImplementedError
    #     # TODO: Implement this
    #     if not isinstance(old, has_linked_pad):
    #         self.pads.update(old.get_pads())
    #         return super().handle_duplicate(old, node)

    #     old.pads.update(self.pads)
    #     return False

    @classmethod
    def MakeChild(cls, pad: fabll._ChildField["F.Pad"]) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(pad)
        return out

    def setup(self, pad: "F.Pad") -> Self:
        self.pad_ptr_.get().point(pad)
        return self
