# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.library._F as F


class has_equal_pins(F.Footprint.TraitT):
    @abstractmethod
    def get_pin_map(self) -> dict[F.Pad, str]: ...
