# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_kicad_footprint_equal_ifs(F.has_kicad_footprint.impl()):
    def get_pin_names(self):
        return self.obj.get_trait(F.has_equal_pins).get_pin_map()
