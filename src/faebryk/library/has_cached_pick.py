# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import TYPE_CHECKING, Self

import faebryk.library._F as F
from faebryk.core.module import Module

if TYPE_CHECKING:
    from faebryk.libs.picker.picker import PickedPart

logger = logging.getLogger(__name__)


class has_cached_pick(Module.TraitT.decless()):
    def __init__(self, has_part_picked: F.has_part_picked):
        super().__init__()
        self._has_part_picked = has_part_picked

    @classmethod
    def by_supplier(
        cls, supplier_id: str, supplier_partno: str, manufacturer: str, partno: str
    ) -> Self:
        return cls(
            F.has_part_picked.by_supplier(
                supplier_id=supplier_id,
                supplier_partno=supplier_partno,
                manufacturer=manufacturer,
                partno=partno,
            )
        )

    def on_obj_set(self):
        obj = self.get_obj(Module)
        obj.add(self._has_part_picked)
        obj.add(F.has_cacheable_pick())

    def get_part(self) -> "PickedPart":
        return self._has_part_picked.get_part()
