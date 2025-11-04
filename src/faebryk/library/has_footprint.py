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

    def set_footprint(self, fp: F.Footprint):
        EdgePointer.point_to(
            bound_node=self.instance,
            target_node=fp.instance.node(),
            identifier="footprint",
            order=None,
        )

    def try_get_footprint(self) -> F.Footprint | None:
        if fps := self.get_children(direct_only=True, types=F.Footprint):
            assert len(fps) == 1, f"In obj: {self}: candidates: {fps}"
            return first(fps)
        else:
            return None

    def get_footprint(self) -> F.Footprint:
        return not_none(self.try_get_footprint())

    @classmethod
    def MakeChild(cls, fp: fabll.ChildField[F.Footprint]):
        out = fabll.ChildField(cls)
        out.add_dependant(
            fabll.EdgeField(
                [out],
                [fp],
                edge=EdgePointer.build(identifier="footprint", order=None),
            )
        )
        return out
