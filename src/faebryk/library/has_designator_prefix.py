# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import ModuleTrait


class has_designator_prefix(ModuleTrait):
    @abstractmethod
    def get_prefix(self) -> str:
        ...
