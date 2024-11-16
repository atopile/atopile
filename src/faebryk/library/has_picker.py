# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.module import Module
from faebryk.core.solver import Solver


class has_picker(Module.TraitT):
    @abstractmethod
    def pick(self, solver: Solver) -> None: ...
