# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.module import Module


class has_designator_prefix(Module.TraitT):
    @abstractmethod
    def get_prefix(self) -> str: ...
