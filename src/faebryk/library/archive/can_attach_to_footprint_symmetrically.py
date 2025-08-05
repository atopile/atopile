# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class can_attach_to_footprint_symmetrically(F.can_attach_to_footprint.impl()):
    def attach(self, footprint: F.Footprint):
        self.obj.add(F.has_footprint_defined(footprint))

        for i, j in zip(
            footprint.get_children(direct_only=True, types=F.Pad),
            self.obj.get_children(direct_only=True, types=F.Electrical),
        ):
            i.attach(j)
