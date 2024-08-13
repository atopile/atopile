# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import Sequence

from faebryk.core.core import ModuleTrait


class has_footprint_requirement(ModuleTrait):
    @abstractmethod
    def get_footprint_requirement(self) -> Sequence[tuple[str, int]]:
        """
        Get tuples of footprint names and pin counts of allowed footprints for this
        module
        """
        ...
