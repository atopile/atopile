# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_switch_power_defined import can_switch_power_defined
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower


class PowerSwitch(Module):
    """
    A generic module that switches power based on a logic signal, needs specialization

    The logic signal is active high. When left floating, the state is determined by the
    normally_closed parameter.
    """

    def __init__(self, normally_closed: bool) -> None:
        super().__init__()

        self.normally_closed = normally_closed

        class _IFs(Module.IFS()):
            logic_in = ElectricLogic()
            power_in = ElectricPower()
            switched_power_out = ElectricPower()

        self.IFs = _IFs(self)

        self.add_trait(
            can_switch_power_defined(
                self.IFs.power_in, self.IFs.switched_power_out, self.IFs.logic_in
            )
        )

        self.IFs.switched_power_out.PARAMs.voltage.merge(
            self.IFs.power_in.PARAMs.voltage
        )
