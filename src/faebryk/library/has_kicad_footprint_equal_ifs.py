# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.has_kicad_footprint import has_kicad_footprint


class has_kicad_footprint_equal_ifs(has_kicad_footprint.impl()):
    def get_pin_names(self):
        from faebryk.library.has_equal_pins import has_equal_pins

        return self.get_obj().get_trait(has_equal_pins).get_pin_map()
