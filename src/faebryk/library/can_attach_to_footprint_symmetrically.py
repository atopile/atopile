# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.can_attach_to_footprint import can_attach_to_footprint
from faebryk.library.Electrical import Electrical
from faebryk.library.Footprint import Footprint
from faebryk.library.has_defined_footprint import has_defined_footprint
from faebryk.library.Pad import Pad


class can_attach_to_footprint_symmetrically(can_attach_to_footprint.impl()):
    def attach(self, footprint: Footprint):
        self.get_obj().add_trait(has_defined_footprint(footprint))
        for i, j in zip(footprint.IFs.get_all(), self.get_obj().IFs.get_all()):
            assert isinstance(i, Pad)
            assert isinstance(j, Electrical)
            assert type(i.IFs.net) is type(j)
            i.attach(j)
