# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from math import sqrt

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.libs.library import L
from faebryk.libs.picker.picker import PickError, has_part_picked_remove
from faebryk.libs.units import P, Quantity


class Resistor(Module):
    unnamed = L.list_field(2, F.Electrical)

    resistance: F.TBD[Quantity]
    rated_power: F.TBD[Quantity]
    rated_voltage: F.TBD[Quantity]

    attach_to_footprint: F.can_attach_to_footprint_symmetrically
    designator_prefix = L.f_field(F.has_designator_prefix_defined)("R")

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(*self.unnamed)

    @L.rt_field
    def simple_value_representation(self):
        from faebryk.core.util import (
            as_unit,
            as_unit_with_tolerance,
        )

        return F.has_simple_value_representation_based_on_params(
            (
                self.resistance,
                self.rated_power,
            ),
            lambda ps: " ".join(
                filter(
                    None,
                    [as_unit_with_tolerance(ps[0], "Ω"), as_unit(ps[1], "W")],
                )
            ),
        )

    def allow_removal_if_zero(self):
        import faebryk.library._F as F

        def replace_zero(m: Module):
            assert m is self

            r = self.resistance.get_most_narrow()
            if not F.Constant(0.0 * P.ohm).is_subset_of(r):
                raise PickError("", self)

            self.resistance.override(F.Constant(0.0 * P.ohm))
            self.unnamed[0].connect(self.unnamed[1])
            self.add_trait(has_part_picked_remove())

        F.has_multi_picker.add_to_module(
            self, -100, F.has_multi_picker.FunctionPicker(replace_zero)
        )

    def get_voltage_drop_by_current_resistance(self, current_A: Parameter) -> Parameter:
        return current_A * self.resistance

    def get_voltage_drop_by_power_resistance(self, power_W: Parameter) -> Parameter:
        return sqrt(power_W * self.resistance)

    @staticmethod
    def set_voltage_drop_by_power_current(
        power_W: Parameter, current_A: Parameter
    ) -> Parameter:
        return power_W / current_A

    def get_current_flow_by_voltage_resistance(
        self, voltage_drop_V: Parameter
    ) -> Parameter:
        return voltage_drop_V / self.resistance

    def get_current_flow_by_power_resistance(self, power_W: Parameter) -> Parameter:
        return sqrt(power_W / self.resistance)

    @staticmethod
    def get_current_flow_by_voltage_power(
        voltage_drop_V: Parameter, power_W: Parameter
    ) -> Parameter:
        return power_W / voltage_drop_V

    def set_resistance_by_voltage_current(
        self, voltage_drop_V: Parameter, current_A: Parameter
    ) -> Parameter:
        self.resistance.merge(voltage_drop_V / current_A)
        return self.resistance.get_most_narrow()

    def set_resistance_by_voltage_power(
        self, voltage_drop_V: Parameter, power_W: Parameter
    ) -> Parameter:
        self.resistance.merge(pow(voltage_drop_V, 2) / power_W)
        return self.resistance.get_most_narrow()

    def set_resistance_by_power_current(
        self, current_A: Parameter, power_W: Parameter
    ) -> Parameter:
        self.resistance.merge(power_W / pow(current_A, 2))
        return self.resistance.get_most_narrow()

    def get_power_dissipation_by_voltage_resistance(
        self, voltage_drop_V: Parameter
    ) -> Parameter:
        return pow(voltage_drop_V, 2) / self.resistance

    def get_power_dissipation_by_current_resistance(
        self, current_A: Parameter
    ) -> Parameter:
        return pow(current_A, 2) * self.resistance

    @staticmethod
    def get_power_dissipation_by_voltage_current(
        voltage_drop_V: Parameter, current_A
    ) -> Parameter:
        return voltage_drop_V * current_A

    def set_rated_power_by_voltage_resistance(self, voltage_drop_V: Parameter):
        self.rated_power.merge(
            self.get_power_dissipation_by_voltage_resistance(voltage_drop_V)
        )

    def set_rated_power_by_current_resistance(self, current_A: Parameter):
        self.rated_power.merge(
            self.get_power_dissipation_by_current_resistance(current_A)
        )
