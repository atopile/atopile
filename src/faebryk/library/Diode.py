# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module, Parameter
from faebryk.core.util import as_unit
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_pin_association_heuristic_lookup_table import (
    has_pin_association_heuristic_lookup_table,
)
from faebryk.library.has_simple_value_representation_based_on_param import (
    has_simple_value_representation_based_on_param,
)
from faebryk.library.TBD import TBD


class Diode(Module):
    @classmethod
    def PARAMS(cls):
        class _PARAMs(super().PARAMS()):
            forward_voltage = TBD[float]()
            max_current = TBD[float]()
            current = TBD[float]()
            reverse_working_voltage = TBD[float]()
            reverse_leakage_current = TBD[float]()

        return _PARAMs

    def __init__(self):
        super().__init__()

        self.PARAMs = self.PARAMS()(self)

        class _IFs(super().IFS()):
            anode = Electrical()
            cathode = Electrical()

        self.IFs = _IFs(self)

        self.add_trait(can_bridge_defined(self.IFs.anode, self.IFs.cathode))
        self.add_trait(
            has_simple_value_representation_based_on_param(
                self.PARAMs.forward_voltage,
                lambda p: as_unit(p, "V"),
            )
        )
        self.add_trait(has_designator_prefix_defined("D"))
        self.add_trait(
            has_pin_association_heuristic_lookup_table(
                mapping={
                    self.IFs.anode: ["A", "Anode", "+"],
                    self.IFs.cathode: ["K", "C", "Cathode", "-"],
                },
                accept_prefix=False,
                case_sensitive=False,
            )
        )

    def get_needed_series_resistance_for_current_limit(
        self, input_voltage_V: Parameter[float]
    ) -> Parameter[float]:
        return (input_voltage_V - self.PARAMs.forward_voltage) / self.PARAMs.current
