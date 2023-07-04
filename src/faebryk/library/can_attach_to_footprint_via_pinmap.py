# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Footprint
from faebryk.library.can_attach_to_footprint import can_attach_to_footprint
from faebryk.library.can_attach_via_pinmap import can_attach_via_pinmap
from faebryk.library.Electrical import Electrical
from faebryk.library.has_defined_footprint import has_defined_footprint


class can_attach_to_footprint_via_pinmap(can_attach_to_footprint.impl()):
    def __init__(self, pinmap: dict[str, Electrical]) -> None:
        super().__init__()
        self.pinmap = pinmap

    def attach(self, footprint: Footprint):
        self.get_obj().add_trait(has_defined_footprint(footprint))
        footprint.get_trait(can_attach_via_pinmap).attach(self.pinmap)
