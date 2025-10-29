# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_equal_pins_in_ifs(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def get_pin_map(self):
        return {
            p: str(i + 1)
            for i, p in enumerate(self.obj.get_children(direct_only=True, types=F.Pad))
        }
