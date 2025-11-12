# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none


class has_footprint(fabll.Node):
    _is_trait = fabll.Traits.MakeChild_Trait(
        fabll._ChildField(fabll.ImplementsTrait).put_on_type()
    )

    footprint_pointer_ = F.Collections.Pointer.MakeChild()

    def set_footprint(self, fp: F.Footprint):
        self.footprint_pointer_.get().point(fp)

    def try_get_footprint(self) -> F.Footprint | None:
        if fp := self.footprint_pointer_.get().deref():
            return F.Footprint.bind_instance(fp.instance)
        else:
            return None

    def get_footprint(self) -> F.Footprint:
        return not_none(self.try_get_footprint())

    @classmethod
    def MakeChild(cls, fp: fabll._ChildField[F.Footprint]):
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Collections.Pointer.EdgeField(
                [out, cls.footprint_pointer_],
                [fp],
            )
        )
        return out
