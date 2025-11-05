# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import TYPE_CHECKING

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.libs.util import not_none

if TYPE_CHECKING:
    from faebryk.library.Footprint import Footprint


class has_footprint(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    footprint_pointer_ = F.Collections.Pointer.MakeChild()

    def set_footprint(self, fp: F.Footprint):
        EdgePointer.point_to(
            bound_node=self.instance,
            target_node=fp.instance.node(),
            identifier="footprint",
            order=None,
        )

    def try_get_footprint(self) -> F.Footprint | None:
        if fps := self.footprint_pointer_.get().deref():
            assert len(fps) == 1, f"In node: {self}: footprint candidates: {fps}"
            return F.Footprint.bind_instance(fps[0].instance)
        else:
            return None

    def get_footprint(self) -> F.Footprint:
        return not_none(self.try_get_footprint())

    @classmethod
    def MakeChild(cls, fp: fabll.ChildField[F.Footprint]):
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Collections.Pointer.EdgeField(
                [out, cls.footprint_pointer_],
                [fp],
            )
        )
        return out
