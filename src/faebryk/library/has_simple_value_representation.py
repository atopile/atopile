# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.module import Module


class has_simple_value_representation(Module.TraitT):
    @abstractmethod
    def get_value(self) -> str: ...
