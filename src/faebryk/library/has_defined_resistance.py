# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Parameter
from faebryk.library.has_resistance import has_resistance


class has_defined_resistance(has_resistance.impl()):
    def __init__(self, resistance: Parameter) -> None:
        super().__init__()
        self.component_resistance = resistance

    def get_resistance(self):
        return self.component_resistance
