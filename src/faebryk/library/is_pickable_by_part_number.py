# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class is_pickable_by_part_number(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    # TODO: make manufacturer an enum
    def __init__(self, manufacturer: str, partno: str):
        super().__init__()
        self._manufacturer = manufacturer
        self._partno = partno

    def get_manufacturer(self) -> str:
        return self._manufacturer

    def get_partno(self) -> str:
        return self._partno
