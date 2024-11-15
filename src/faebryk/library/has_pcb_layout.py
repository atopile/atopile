# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.module import Module


class has_pcb_layout(Module.TraitT):
    @abstractmethod
    def apply(self): ...
