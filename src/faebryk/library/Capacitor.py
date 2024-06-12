# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import IntEnum, auto

from faebryk.core.core import Module
from faebryk.core.util import as_unit, as_unit_with_tolerance
from faebryk.library.can_attach_to_footprint_symmetrically import (
    can_attach_to_footprint_symmetrically,
)
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_simple_value_representation_based_on_params import (
    has_simple_value_representation_based_on_params,
)
from faebryk.library.TBD import TBD
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class Capacitor(Module):
    class TemperatureCoefficient(IntEnum):
        Y5V = auto()
        Z5U = auto()
        X7S = auto()
        X5R = auto()
        X6R = auto()
        X7R = auto()
        X8R = auto()
        C0G = auto()

    def __init__(self):
        super().__init__()

        class _IFs(Module.IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            capacitance = TBD[float]()
            rated_voltage = TBD[float]()
            temperature_coefficient = TBD[Capacitor.TemperatureCoefficient]()

        self.PARAMs = _PARAMs(self)

        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

        self.add_trait(
            has_simple_value_representation_based_on_params(
                (
                    self.PARAMs.capacitance,
                    self.PARAMs.rated_voltage,
                    self.PARAMs.temperature_coefficient,
                ),
                lambda ps: f"{as_unit_with_tolerance(ps[0], 'F')} "
                f"{as_unit(ps[1].max, 'V')} "
                f"{ps[2].max.value.name}",
            )
        )
        self.add_trait(can_attach_to_footprint_symmetrically())
        self.add_trait(has_designator_prefix_defined("C"))
