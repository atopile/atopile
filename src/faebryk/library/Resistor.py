# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from math import sqrt

from faebryk.core.core import Module, Parameter
from faebryk.core.util import (
    as_unit,
    as_unit_with_tolerance,
)
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


class Resistor(Module):
    def __init__(self):
        super().__init__()

        class _IFs(super().IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)
        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

        class PARAMS(super().PARAMS()):
            resistance = TBD[float]()
            rated_power = TBD[float]()

        self.PARAMs = PARAMS(self)

        self.add_trait(can_attach_to_footprint_symmetrically())
        self.add_trait(
            has_simple_value_representation_based_on_params(
                (
                    self.PARAMs.resistance,
                    self.PARAMs.rated_power,
                ),
                lambda ps: f"{as_unit_with_tolerance(ps[0], 'Ω')} "
                f"{as_unit(ps[1].max, 'W')}",
            )
        )
        self.add_trait(has_designator_prefix_defined("R"))

    def get_voltage_drop_by_current_resistance(self, current_A: Parameter) -> Parameter:
        return current_A * self.PARAMs.resistance

    def get_voltage_drop_by_power_resistance(self, power_W: Parameter) -> Parameter:
        return sqrt(power_W * self.PARAMs.resistance)

    @staticmethod
    def set_voltage_drop_by_power_current(
        power_W: Parameter, current_A: Parameter
    ) -> Parameter:
        return power_W / current_A

    def get_current_flow_by_voltage_resistance(
        self, voltage_drop_V: Parameter
    ) -> Parameter:
        return voltage_drop_V / self.PARAMs.resistance

    def get_current_flow_by_power_resistance(self, power_W: Parameter) -> Parameter:
        return sqrt(power_W / self.PARAMs.resistance)

    @staticmethod
    def get_current_flow_by_voltage_power(
        voltage_drop_V: Parameter, power_W: Parameter
    ) -> Parameter:
        return power_W / voltage_drop_V

    def set_resistance_by_voltage_current(
        self, voltage_drop_V: Parameter, current_A: Parameter
    ) -> Parameter:
        self.PARAMs.resistance.merge(voltage_drop_V / current_A)
        return self.PARAMs.resistance.get_most_narrow()

    def set_resistance_by_voltage_power(
        self, voltage_drop_V: Parameter, power_W: Parameter
    ) -> Parameter:
        self.PARAMs.resistance.merge(pow(voltage_drop_V, 2) / power_W)
        return self.PARAMs.resistance.get_most_narrow()

    def set_resistance_by_power_current(
        self, current_A: Parameter, power_W: Parameter
    ) -> Parameter:
        self.PARAMs.resistance.merge(power_W / pow(current_A, 2))
        return self.PARAMs.resistance.get_most_narrow()

    def get_power_dissipation_by_voltage_resistance(
        self, voltage_drop_V: Parameter
    ) -> Parameter:
        return pow(voltage_drop_V, 2) / self.PARAMs.resistance

    def get_power_dissipation_by_current_resistance(
        self, current_A: Parameter
    ) -> Parameter:
        return pow(current_A, 2) * self.PARAMs.resistance

    @staticmethod
    def get_power_dissipation_by_voltage_current(
        voltage_drop_V: Parameter, current_A
    ) -> Parameter:
        return voltage_drop_V * current_A

    def set_rated_power_by_voltage_resistance(self, voltage_drop_V: Parameter):
        self.PARAMs.rated_power.merge(
            self.get_power_dissipation_by_voltage_resistance(voltage_drop_V)
        )

    def set_rated_power_by_current_resistance(self, current_A: Parameter):
        self.PARAMs.rated_power.merge(
            self.get_power_dissipation_by_current_resistance(current_A)
        )
