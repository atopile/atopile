# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import TYPE_CHECKING, Self

from faebryk.core.module import Module
from faebryk.libs.util import not_none

if TYPE_CHECKING:
    from faebryk.libs.picker.picker import PickedPart

logger = logging.getLogger(__name__)


class has_part_picked(Module.TraitT.decless()):
    def __init__(self, part: "PickedPart | None") -> None:
        """
        None = remove part from netlist
        """
        super().__init__()
        if type(self) is has_part_picked and part is None:
            raise ValueError("Use has_part_picked.remove()")
        self.part = part

    @classmethod
    def by_supplier(
        cls, supplier_id: str, supplier_partno: str, manufacturer: str, partno: str
    ) -> Self:
        from faebryk.libs.picker.lcsc import PickedPartLCSC

        match supplier_id:
            case "lcsc":
                return cls(
                    PickedPartLCSC(
                        manufacturer=manufacturer,
                        partno=partno,
                        supplier_partno=supplier_partno,
                    )
                )
            case _:
                raise ValueError(f"Unknown supplier: {supplier_id}")

    def get_part(self) -> "PickedPart":
        return not_none(self.part)

    def try_get_part(self) -> "PickedPart | None":
        return self.part

    @property
    def removed(self) -> bool:
        return self.part is None
