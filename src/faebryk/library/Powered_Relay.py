# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.Diode import Diode
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.PoweredLED import PoweredLED
from faebryk.library.PowerSwitchMOSFET import PowerSwitchMOSFET
from faebryk.library.Relay import Relay

logger = logging.getLogger(__name__)


class Powered_Relay(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            relay = Relay()
            indicator = PoweredLED()
            flyback_diode = Diode()
            relay_driver = PowerSwitchMOSFET(lowside=True, normally_closed=False)

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            switch_a_nc = Electrical()
            switch_a_common = Electrical()
            switch_a_no = Electrical()
            switch_b_no = Electrical()
            switch_b_common = Electrical()
            switch_b_nc = Electrical()
            enable = ElectricLogic()
            power = ElectricPower()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        self.NODEs.relay.IFs.switch_a_common.connect(self.IFs.switch_a_common)
        self.NODEs.relay.IFs.switch_a_nc.connect(self.IFs.switch_a_nc)
        self.NODEs.relay.IFs.switch_a_no.connect(self.IFs.switch_a_no)
        self.NODEs.relay.IFs.switch_b_common.connect(self.IFs.switch_b_common)
        self.NODEs.relay.IFs.switch_b_nc.connect(self.IFs.switch_b_nc)
        self.NODEs.relay.IFs.switch_b_no.connect(self.IFs.switch_b_no)

        self.NODEs.relay_driver.IFs.power_in.connect(self.IFs.power)
        self.NODEs.relay_driver.IFs.logic_in.connect(self.IFs.enable)
        self.NODEs.relay_driver.IFs.switched_power_out.IFs.lv.connect(
            self.NODEs.relay.IFs.coil_n
        )
        self.NODEs.relay_driver.IFs.switched_power_out.IFs.hv.connect(
            self.NODEs.relay.IFs.coil_p
        )

        self.NODEs.relay.IFs.coil_n.connect_via(
            self.NODEs.flyback_diode, self.NODEs.relay.IFs.coil_p
        )

        self.NODEs.indicator.IFs.power.connect(
            self.NODEs.relay_driver.IFs.switched_power_out
        )
