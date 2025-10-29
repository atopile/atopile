# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_kicad_footprint_equal_ifs_defined(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(self, str) -> None:
        super().__init__()
        self.str = str

    def get_kicad_footprint(self):
        return self.str
