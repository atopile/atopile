# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P
from faebryk.libs.util import assert_once  # noqa: F401

logger = logging.getLogger(__name__)


class TPS2116_ReferenceDesign(Module):
    """
    2 to 1, 1.6 V to 5.5 V, 2.5-A Low IQ Power Mux with Manual and Priority Switchover
    """

    class Mode(Enum):
        MANUAL = 0
        """
        Manually tie mode to an external power reference.
        If select is above Vref (1V), power_in[0] is selected.
        If select is below Vref, power_in[1] is selected.
        """
        PRIORITY = 1
        """
        This is the most automatic mode.
        power_in[0] is selected by default, switchover only happens if power_in[0] is
        lower than power_in[1].
        """
        SHUTDOWN = 2
        """
        Disables device.
        """

    class SwitchoverVoltage(Enum):
        _5V = auto()
        _3V3 = auto()
        _1V8 = auto()
        CUSTOM = auto()

    @assert_once
    def set_mode(self, mode: Mode, switchover_voltage: SwitchoverVoltage):
        if mode == self.Mode.PRIORITY:
            self.tps2116.mode.set(on=True)
            self.tps2116.power_in[0].connect(self.resistor_divider.power)
            self.tps2116.select.connect(self.resistor_divider.output)
            if switchover_voltage != self.SwitchoverVoltage.CUSTOM:
                self.resistor_divider.r_bottom.resistance.constrain_subset(
                    L.Range.from_center_rel(5 * P.kohm, 0.01)
                )
            if switchover_voltage == self.SwitchoverVoltage._5V:
                self.resistor_divider.r_top.resistance.constrain_subset(
                    L.Range.from_center_rel(16.9 * P.kohm, 0.01)
                )
            elif switchover_voltage == self.SwitchoverVoltage._3V3:
                self.resistor_divider.r_top.resistance.constrain_subset(
                    L.Range.from_center_rel(9.53 * P.kohm, 0.01)
                )
            elif switchover_voltage == self.SwitchoverVoltage._1V8:
                self.resistor_divider.r_top.resistance.constrain_subset(
                    L.Range.from_center_rel(2.80 * P.kohm, 0.01)
                )
        else:
            raise NotImplementedError(f"Mode {mode} not implemented")

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    tps2116: F.TPS2116
    resistor_divider: F.ResistorVoltageDivider

    power_in = L.list_field(2, F.ElectricPower)
    power_out: F.ElectricPower
    status: F.ElectricLogic

    # ----------------------------------------
    #                 traits
    # ----------------------------------------

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        self.tps2116.power_in[0].connect(self.power_in[0])
        self.tps2116.power_in[1].connect(self.power_in[1])
        self.tps2116.power_out.connect(self.power_out)
        self.tps2116.status.connect(self.status)
        # ------------------------------------
        #          parametrization
        # ------------------------------------
