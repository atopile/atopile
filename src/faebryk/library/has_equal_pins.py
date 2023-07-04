# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import FootprintTrait
from faebryk.library.Electrical import Electrical


class has_equal_pins(FootprintTrait):
    @abstractmethod
    def get_pin_map(self) -> dict[Electrical, str]:
        ...
