# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.library._F as F


class is_pickable_by_supplier_id(F.is_pickable.decless()):
    class Supplier(Enum):
        LCSC = auto()

    def __init__(self, supplier_part_id: str, supplier: Supplier = Supplier.LCSC):
        super().__init__()
        self._supplier_part_id = supplier_part_id
        self._supplier = supplier

    def get_supplier_part_id(self) -> str:
        return self._supplier_part_id

    def get_supplier(self) -> Supplier:
        return self._supplier
