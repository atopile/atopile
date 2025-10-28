# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_pin_association_heuristic(fabll.Node):
    class PinMatchException(Exception): ...

    """
    Get the pinmapping for a list of pins based on a heuristic.
    """

    @abstractmethod
    def get_pins(
        self,
        pins: list[tuple[str, str]],
    ) -> dict[str, F.Electrical]: ...
