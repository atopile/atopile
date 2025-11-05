# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
from faebryk.library import _F as F


class can_attach_to_footprint_symmetrically(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    # TODO: Forward this trait to parent
    _has_footprint = fabll.ChildField(F.has_footprint)

    def attach(self, footprint: F.Footprint):
        self.get_trait(F.has_footprint).set_footprint(footprint)

        for i, j in zip(
            footprint.get_children(direct_only=True, types=F.Pad),
            self.get_children(direct_only=True, types=F.Electrical),
        ):
            i.attach(j)
