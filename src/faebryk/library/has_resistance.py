# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import ModuleTrait, Parameter


class has_resistance(ModuleTrait):
    @abstractmethod
    def get_resistance(self) -> Parameter: ...
