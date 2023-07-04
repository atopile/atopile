# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import FootprintTrait
from faebryk.library.Electrical import Electrical


class has_kicad_footprint(FootprintTrait):
    @abstractmethod
    def get_kicad_footprint(self) -> str:
        ...

    @abstractmethod
    def get_pin_names(self) -> dict[Electrical, str]:
        ...
