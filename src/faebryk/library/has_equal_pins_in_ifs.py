# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.has_equal_pins import has_equal_pins
from faebryk.library.Pad import Pad


class has_equal_pins_in_ifs(has_equal_pins.impl()):
    def get_pin_map(self):
        return {
            p: str(i + 1)
            for i, p in enumerate(self.get_obj().IFs.get_all())
            if isinstance(p, Pad)
        }
