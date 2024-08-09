# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.Range import Range
from faebryk.library.TBD import TBD

logger = logging.getLogger(__name__)


class LDO(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            power_in = ElectricPower()
            power_out = ElectricPower()
            enable = ElectricLogic()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()):
            output_voltage = TBD[float]()
            dropout_voltage = TBD[float]()
            input_voltage_range = TBD[Range]()
            output_current_max = TBD[float]()
            quiescent_current = TBD[float]()

        self.PARAMs = _PARAMs(self)

        self.IFs.power_in.PARAMs.voltage.merge(self.PARAMs.input_voltage_range)
        self.IFs.power_out.PARAMs.voltage.merge(self.PARAMs.output_voltage)

        self.IFs.power_in.get_trait(can_be_decoupled).decouple()
        self.IFs.power_out.get_trait(can_be_decoupled).decouple()

        self.IFs.power_in.IFs.lv.connect(self.IFs.power_out.IFs.lv)

        self.add_trait(has_designator_prefix_defined("U"))

        self.add_trait(can_bridge_defined(self.IFs.power_in, self.IFs.power_out))
