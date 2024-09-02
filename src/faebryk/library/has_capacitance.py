# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.module import Module
from faebryk.core.parameter import Parameter


class has_capacitance(Module.TraitT):
    @abstractmethod
    def get_capacitance(self) -> Parameter: ...
