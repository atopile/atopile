# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.library.Electrical import Electrical
from faebryk.library.FootprintTrait import FootprintTrait


class can_attach_via_pinmap(FootprintTrait):
    @abstractmethod
    def attach(self, pinmap: dict[str, Electrical]): ...
