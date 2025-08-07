# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.parameter import Parameter


class is_representable_by_single_value(Parameter.TraitT):
    @abstractmethod
    def get_single_representing_value(self): ...
