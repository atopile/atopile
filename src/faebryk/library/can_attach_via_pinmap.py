# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import FootprintTrait
from faebryk.library.Electrical import Electrical


class can_attach_via_pinmap(FootprintTrait):
    @abstractmethod
    def attach(self, pinmap: dict[str, Electrical]):
        ...
