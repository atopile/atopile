# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.module import Module
from faebryk.core.parameter import Parameter


class has_resistance(Module.TraitT):
    @abstractmethod
    def get_resistance(self) -> Parameter: ...
