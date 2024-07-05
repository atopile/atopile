# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.can_attach_via_pinmap import can_attach_via_pinmap
from faebryk.library.Electrical import Electrical
from faebryk.library.has_equal_pins import has_equal_pins


class can_attach_via_pinmap_equal(can_attach_via_pinmap.impl()):
    def attach(self, pinmap: dict[str, Electrical]):
        pin_list = {
            v: k
            for k, v in self.get_obj().get_trait(has_equal_pins).get_pin_map().items()
        }
        for no, intf in pinmap.items():
            pin_list[no].attach(intf)
