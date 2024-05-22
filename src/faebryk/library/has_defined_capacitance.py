# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Parameter
from faebryk.library.has_capacitance import has_capacitance


class has_defined_capacitance(has_capacitance.impl()):
    def __init__(self, capacitance: Parameter) -> None:
        super().__init__()
        self.component_capacitance = capacitance

    def get_capacitance(self):
        return self.component_capacitance
