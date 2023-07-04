# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import ModuleTrait


class has_type_description(ModuleTrait):
    @abstractmethod
    def get_type_description(self) -> str:
        ...
