# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module, NodeTrait, Parameter
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.has_defined_type_description import has_defined_type_description
from faebryk.library.TBD import TBD


class LED(Module):
    class has_calculatable_needed_series_resistance(NodeTrait):
        @staticmethod
        def get_needed_series_resistance_ohm(input_voltage_V: float) -> Constant:
            raise NotImplementedError

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("LED"))

        class _(self.has_calculatable_needed_series_resistance.impl()):
            @staticmethod
            def get_needed_series_resistance_ohm(input_voltage_V: float) -> Constant:
                assert isinstance(self.voltage_V, Constant)
                assert isinstance(self.current_A, Constant)
                return LED.needed_series_resistance_ohm(
                    input_voltage_V, self.voltage_V.value, self.current_A.value
                )

            def is_implemented(self):
                obj = self.get_obj()
                assert isinstance(obj, LED)
                return isinstance(obj.voltage_V, Constant) and isinstance(
                    obj.current_A, Constant
                )

        self.add_trait(_())

        self.add_trait(has_defined_type_description("D"))

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            anode = Electrical()
            cathode = Electrical()

        self.IFs = _IFs(self)

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()
        self.set_forward_parameters(TBD(), TBD())

    def set_forward_parameters(self, voltage_V: Parameter, current_A: Parameter):
        self.voltage_V = voltage_V
        self.current_A = current_A

    @staticmethod
    def needed_series_resistance_ohm(
        input_voltage_V: float, forward_voltage_V: float, forward_current_A: float
    ) -> Constant:
        return Constant(int((input_voltage_V - forward_voltage_V) / forward_current_A))
