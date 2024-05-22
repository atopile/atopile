# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import ModuleTrait


class has_simple_value_representation(ModuleTrait):
    @abstractmethod
    def get_value(self) -> str:
        ...
