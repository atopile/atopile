# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import TYPE_CHECKING

from faebryk.core.module import Module
from faebryk.libs.util import not_none

if TYPE_CHECKING:
    from faebryk.libs.picker.picker import Part

logger = logging.getLogger(__name__)


class has_part_picked(Module.TraitT.decless()):
    def __init__(self, part: "Part | None") -> None:
        """
        None = remove part from netlist
        """
        super().__init__()
        if type(self) is has_part_picked and part is None:
            raise ValueError("Use has_part_picked.remove()")
        self.part = part

    def get_part(self) -> "Part":
        return not_none(self.part)

    def try_get_part(self) -> "Part | None":
        return self.part

    @property
    def removed(self) -> bool:
        return self.part is None
