# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from math import sqrt

from faebryk.core.core import Module, Parameter
from faebryk.core.util import unit_map
from faebryk.library.can_attach_to_footprint_symmetrically import (
    can_attach_to_footprint_symmetrically,
)
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.has_defined_resistance import has_defined_resistance
from faebryk.library.has_resistance import has_resistance
from faebryk.library.has_type_description import has_type_description
from faebryk.libs.util import times


class Resistor(Module):
    def _setup_traits(self):
        self.add_trait(can_attach_to_footprint_symmetrically())

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)
        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self, resistance: Parameter):
        super().__init__()
        self._setup_interfaces()
        self.set_resistance(resistance)

    def set_resistance(self, resistance: Parameter):
        self.add_trait(has_defined_resistance(resistance))

        if type(resistance) is not Constant:
            # TODO this is a bit ugly
            # it might be that there was another more abstract valid trait
            # but this challenges the whole trait overriding mechanism
            # might have to make a trait stack thats popped or so
            self.del_trait(has_type_description)
            return

        class _has_type_description(has_type_description.impl()):
            @staticmethod
            def get_type_description():
                assert isinstance(
                    self.get_trait(has_resistance).get_resistance(), Constant
                )
                resistance = self.get_trait(has_resistance).get_resistance()
                assert isinstance(resistance, Constant)
                return unit_map(
                    resistance.value, ["µΩ", "mΩ", "Ω", "KΩ", "MΩ", "GΩ"], start="Ω"
                )

        self.add_trait(_has_type_description())

    def get_voltage_drop_by_current_resistance(self, current_A: Constant) -> Constant:
        resistance = self.get_trait(has_resistance).get_resistance()
        assert isinstance(resistance, Constant)
        voltage_drop = current_A.value * resistance.value
        return Constant(voltage_drop)

    def get_voltage_drop_by_power_resistance(self, power_W: Constant) -> Constant:
        resistance = self.get_trait(has_resistance).get_resistance()
        assert isinstance(resistance, Constant)
        voltage_drop = sqrt(resistance.value * power_W.value)
        return Constant(voltage_drop)

    def get_voltage_drop_by_power_current(
        self, power_W: Constant, current_A: Constant
    ) -> Constant:
        voltage_drop = power_W.value / current_A
        return Constant(voltage_drop)

    def get_current_flow_by_voltage_resistance(
        self, voltage_drop_V: Constant
    ) -> Constant:
        resistance = self.get_trait(has_resistance).get_resistance()
        assert isinstance(resistance, Constant)
        current_flow = voltage_drop_V.value / resistance.value
        return Constant(current_flow)

    def get_current_flow_by_power_resistance(self, power_W: Constant) -> Constant:
        resistance = self.get_trait(has_resistance).get_resistance()
        assert isinstance(resistance, Constant)
        current_flow = sqrt(power_W.value / resistance.value)
        return Constant(current_flow)

    def get_current_flow_by_voltage_power(
        self, voltage_drop_V: Constant, power_W: Constant
    ) -> Constant:
        current_flow = power_W.value / voltage_drop_V.value
        return Constant(current_flow)

    def get_resistance_by_voltage_current(
        self, voltage_drop_V: Constant, current_A: Constant
    ) -> Constant:
        resistance: Constant = voltage_drop_V.value / current_A.value
        self.add_trait(has_defined_resistance(resistance))
        return Constant(resistance)

    def get_resistance_by_voltage_power(
        self, voltage_drop_V: Constant, power_W: Constant
    ) -> Constant:
        resistance: Constant = pow(voltage_drop_V.value, 2) / power_W.value
        self.add_trait(has_defined_resistance(resistance))
        return Constant(resistance)

    def get_resistance_by_power_current(
        self, current_A: Constant, power_W: Constant
    ) -> Constant:
        resistance: Constant = power_W.value / pow(current_A.value, 2)
        self.add_trait(has_defined_resistance(resistance))
        return Constant(resistance)

    def get_power_dissipation_by_voltage_resistance(
        self, voltage_drop_V: Constant
    ) -> Constant:
        resistance = self.get_trait(has_resistance).get_resistance()
        assert isinstance(resistance, Constant)
        energy_dissipation = pow(voltage_drop_V.value, 2) / resistance
        return Constant(energy_dissipation)

    def get_power_dissipation_by_current_resistance(
        self, current_A: Constant
    ) -> Constant:
        resistance = self.get_trait(has_resistance).get_resistance()
        assert isinstance(resistance, Constant)
        energy_dissipation = pow(current_A.value, 2) * resistance
        return Constant(energy_dissipation)

    def get_power_dissipation_by_voltage_current(
        self, voltage_drop_V: Constant, current_A
    ) -> Constant:
        energy_dissipation = voltage_drop_V.value * current_A.value
        return Constant(energy_dissipation)
