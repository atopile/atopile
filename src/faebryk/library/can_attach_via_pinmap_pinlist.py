# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.can_attach_via_pinmap import can_attach_via_pinmap
from faebryk.library.Electrical import Electrical


class can_attach_via_pinmap_pinlist(can_attach_via_pinmap.impl()):
    def __init__(self, pin_list: dict[str, Electrical]) -> None:
        super().__init__()
        self.pin_list = pin_list

    def attach(self, pinmap: dict[str, Electrical]):
        for no, intf in pinmap.items():
            assert (
                no in self.pin_list
            ), f"Pin {no} not in pin list: {self.pin_list.keys()}"
            self.pin_list[no].connect(intf)
