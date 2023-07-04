# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.MOSFET import MOSFET
from faebryk.library.Resistor import Resistor
from faebryk.library.TBD import TBD


class PowerSwitch(Module):
    def __init__(self, lowside: bool, normally_closed: bool) -> None:
        super().__init__()  # interfaces

        self.lowside = lowside
        self.normally_closed = normally_closed

        class _IFs(Module.IFS()):
            logic_in = ElectricLogic()
            power_in = ElectricPower()
            switched_power_out = ElectricPower()

        self.IFs = _IFs(self)

        # components
        class _NODEs(Module.NODES()):
            mosfet = MOSFET(
                MOSFET.ChannelType.N_CHANNEL
                if lowside
                else MOSFET.ChannelType.P_CHANNEL,
                MOSFET.SaturationType.ENHANCEMENT,
            )
            pull_resistor = Resistor(TBD())

        self.NODEs = _NODEs(self)

        # pull gate
        if lowside and not normally_closed:
            self.IFs.logic_in.pull_down(self.NODEs.pull_resistor)
        else:
            self.IFs.logic_in.pull_up(self.NODEs.pull_resistor)

        # connect gate to logic
        self.IFs.logic_in.NODEs.signal.connect(self.NODEs.mosfet.IFs.gate)

        # passthrough non-switched side, bridge switched side
        if lowside:
            self.IFs.power_in.NODEs.hv.connect(self.IFs.switched_power_out.NODEs.hv)
            self.IFs.power_in.NODEs.lv.connect_via(
                self.NODEs.mosfet, self.IFs.switched_power_out.NODEs.lv
            )
        else:
            self.IFs.power_in.NODEs.lv.connect(self.IFs.switched_power_out.NODEs.lv)
            self.IFs.power_in.NODEs.hv.connect_via(
                self.NODEs.mosfet, self.IFs.switched_power_out.NODEs.hv
            )

        # TODO pretty confusing
        # Add bridge trait
        self.add_trait(
            can_bridge_defined(self.IFs.power_in, self.IFs.switched_power_out)
        )

        # TODO do more with logic
        #   e.g check reference being same as power
