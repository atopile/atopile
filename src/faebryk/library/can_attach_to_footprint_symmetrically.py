# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from pint.util import create_class_with_registry
import faebryk.core.node as fabll
from faebryk.library import _F as F


class can_attach_to_footprint_symmetrically(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    electricals_ = F.Collections.PointerSet.MakeChild()

    # TODO: Forward this trait to parent
    _can_attach_to_footprint = fabll.ChildField(F.can_attach_to_footprint)

    def attach(self, footprint: F.Footprint):
        # TODO: Forward this trait to parent*2
        has_footprint = fabll.Traits.create_and_add_instance_to(
            node=self, trait=F.has_footprint
        )
        has_footprint.set_footprint(footprint)

        for i, j in zip(
            footprint.get_children(direct_only=True, types=F.Pad),
            self.electricals_.get().as_list(),
        ):
            i.attach(j)

    @classmethod
    def MakeChild(
        cls, *electricals: fabll.ChildField[F.Electrical]
    ) -> fabll.ChildField:
        out = fabll.ChildField(cls)
        for electrical in electricals:
            out.add_dependant(
                F.Collections.PointerSet.EdgeField(
                    [out, cls.electricals_],
                    [electrical],
                )
            )
        return out
