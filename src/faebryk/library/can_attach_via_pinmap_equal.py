# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class can_attach_via_pinmap_equal(F.can_attach_via_pinmap.impl()):
    def attach(self, pinmap: dict[str, F.Electrical]):
        pin_list = {
            v: k for k, v in self.obj.get_trait(F.has_equal_pins).get_pin_map().items()
        }
        for no, intf in pinmap.items():
            pin_list[no].attach(intf)
