# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import ParameterTrait


class is_representable_by_single_value(ParameterTrait):
    @abstractmethod
    def get_single_representing_value(self): ...
