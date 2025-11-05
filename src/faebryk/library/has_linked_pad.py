# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import TYPE_CHECKING

import faebryk.core.node as fabll
import faebryk.library._F as F

if TYPE_CHECKING:
    from faebryk.library.Pad import Pad


class has_linked_pad(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()
    pad_ptr_ = F.Collections.Pointer.MakeChild()

    def get_pads(self) -> set["Pad"]:
        return self.pad_ptr_.get().deref()  # type: ignore

    def handle_duplicate(self, old: fabll.Node, node: fabll.Node) -> bool:
        raise NotImplementedError
        # TODO: Implement this
        if not isinstance(old, has_linked_pad):
            self.pads.update(old.get_pads())
            return super().handle_duplicate(old, node)

        old.pads.update(self.pads)
        return False

    @classmethod
    def MakeChild(cls, pad: fabll.ChildField["F.Pad"]) -> fabll.ChildField:
        out = fabll.ChildField(cls)
        out.add_dependant(pad)
        return out
