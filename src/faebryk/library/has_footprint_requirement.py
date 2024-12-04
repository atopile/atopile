# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import Sequence

from faebryk.core.module import Module


class has_footprint_requirement(Module.TraitT):
    @abstractmethod
    def get_footprint_requirement(self) -> Sequence[tuple[str, int | None]]:
        """
        Get tuples of footprint names and pin counts of allowed footprints for this
        module
        """
