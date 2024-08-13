# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import ModuleTrait
from faebryk.library.Electrical import Electrical


class has_pin_association_heuristic(ModuleTrait):
    class PinMatchException(Exception): ...

    """
    Get the pinmapping for a list of pins based on a heuristic.
    """

    @abstractmethod
    def get_pins(
        self,
        pins: list[tuple[str, str]],
    ) -> dict[str, Electrical]: ...
