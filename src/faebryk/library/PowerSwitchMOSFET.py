# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.can_switch_power_defined import can_switch_power_defined
from faebryk.library.Constant import Constant
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.MOSFET import MOSFET
from faebryk.library.Resistor import Resistor


class PowerSwitchMOSFET(Module):
    def __init__(self, lowside: bool, normally_closed: bool) -> None:
        super().__init__()

        self.lowside = lowside
        self.normally_closed = normally_closed

        class _IFs(Module.IFS()):
            logic_in = ElectricLogic()
            power_in = ElectricPower()
            switched_power_out = ElectricPower()

        self.IFs = _IFs(self)

        # components
        class _NODEs(Module.NODES()):
            mosfet = MOSFET()
            pull_resistor = Resistor()

        self.NODEs = _NODEs(self)

        self.NODEs.mosfet.PARAMs.channel_type.merge(
            Constant(
                MOSFET.ChannelType.N_CHANNEL
                if lowside
                else MOSFET.ChannelType.P_CHANNEL
            )
        )
        self.NODEs.mosfet.PARAMs.saturation_type.merge(
            Constant(MOSFET.SaturationType.ENHANCEMENT)
        )

        # pull gate
        self.IFs.logic_in.get_trait(ElectricLogic.can_be_pulled).pull(
            lowside and not normally_closed
        )

        # connect gate to logic
        self.IFs.logic_in.IFs.signal.connect(self.NODEs.mosfet.IFs.gate)

        # passthrough non-switched side, bridge switched side
        if lowside:
            self.IFs.power_in.IFs.hv.connect(self.IFs.switched_power_out.IFs.hv)
            self.IFs.power_in.IFs.lv.connect_via(
                self.NODEs.mosfet, self.IFs.switched_power_out.IFs.lv
            )
        else:
            self.IFs.power_in.IFs.lv.connect(self.IFs.switched_power_out.IFs.lv)
            self.IFs.power_in.IFs.hv.connect_via(
                self.NODEs.mosfet, self.IFs.switched_power_out.IFs.hv
            )

        # TODO do more with logic
        #   e.g check reference being same as power

        self.add_trait(
            can_switch_power_defined(
                self.IFs.power_in, self.IFs.switched_power_out, self.IFs.logic_in
            )
        )
