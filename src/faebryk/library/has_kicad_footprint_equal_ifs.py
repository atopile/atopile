# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_kicad_footprint_equal_ifs(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def get_pin_names(self):
        return self.obj.get_trait(F.has_equal_pins).get_pin_map()
