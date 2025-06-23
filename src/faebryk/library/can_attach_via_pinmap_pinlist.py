# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class can_attach_via_pinmap_pinlist(F.can_attach_via_pinmap.impl()):
    def __init__(self, pin_list: dict[str, F.Pad]) -> None:
        super().__init__()
        self.pin_list = pin_list

    def attach(self, pinmap: dict[str, F.Electrical | None]):
        for no, intf in pinmap.items():
            if intf is None:
                continue
            assert no in self.pin_list, (
                f"Pin {no} not in pin list: {self.pin_list.keys()}"
            )
            self.pin_list[no].attach(intf)
