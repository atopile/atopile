# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Footprint, ModuleInterface
from faebryk.library.can_attach_to_footprint import can_attach_to_footprint
from faebryk.library.has_defined_footprint import has_defined_footprint


class can_attach_to_footprint_symmetrically(can_attach_to_footprint.impl()):
    def attach(self, footprint: Footprint):
        self.get_obj().add_trait(has_defined_footprint(footprint))
        for i, j in zip(footprint.IFs.get_all(), self.get_obj().IFs.get_all()):
            assert isinstance(i, ModuleInterface)
            assert isinstance(j, ModuleInterface)
            assert type(i) == type(j)
            i.connect(j)
