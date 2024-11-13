# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P
from faebryk.libs.util import assert_once  # noqa: F401

logger = logging.getLogger(__name__)


class TPS2116(F.PowerMux):
    """
    2 to 1 1.6 V to 5.5 V, 2.5-A Low IQ Power Mux with Manual and Priority Switchover
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
            self.mode.signal.connect(self.power_in[1].hv)
            resistor_devider = self.select.add(F.ResistorVoltageDivider())
            self.power_in[0].hv.connect_via(resistor_devider, self.select.signal)
            resistor_devider.node[2].connect(self.power_in[0].lv)
            if switchover_voltage != self.SwitchoverVoltage.CUSTOM:
                resistor_devider.resistor[1].resistance.constrain_subset(
                    L.Range.from_center_rel(5 * P.kohm, 0.01)
                )
            if switchover_voltage == self.SwitchoverVoltage._5V:
                resistor_devider.resistor[0].resistance.constrain_subset(
                    L.Range.from_center_rel(16.9 * P.kohm, 0.01)
                )
            elif switchover_voltage == self.SwitchoverVoltage._3V3:
                resistor_devider.resistor[0].resistance.constrain_subset(
                    L.Range.from_center_rel(9.53 * P.kohm, 0.01)
                )
            elif switchover_voltage == self.SwitchoverVoltage._1V8:
                resistor_devider.resistor[0].resistance.constrain_subset(
                    L.Range.from_center_rel(2.80 * P.kohm, 0.01)
                )
        else:
            raise NotImplementedError(f"Mode {mode} not implemented")

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    mode: F.ElectricLogic
    status: F.ElectricLogic

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Texas Instruments",
            DescriptiveProperties.partno: "TPS2116DRLR",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.ti.com/lit/ds/symlink/tps2116.pdf"
    )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": self.power_out.lv,
                "2": self.power_out.hv,
                "3": self.power_in[0].hv,
                "4": self.select.signal,
                "5": self.mode.signal,
                "6": self.power_in[1].hv,
                "7": self.power_out.hv,
                "8": self.status.signal,
            },
        )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.power_in[0].lv: ["GND"],
                self.mode.signal: ["MODE"],
                self.select.signal: ["PR1"],
                self.status.signal: ["ST"],
                self.power_in[0].hv: ["VIN1"],
                self.power_in[1].hv: ["VIN2"],
                self.power_out.hv: ["VOUT"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        F.ElectricLogic.connect_all_module_references(self, gnd_only=True)
        F.ElectricLogic.connect_all_module_references(
            self, exclude=[self.power_out, self.power_in[1]]
        )

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        for power in [self.power_in[0], self.power_in[1], self.power_out]:
            power.voltage.constrain_subset(L.Range(1.6 * P.V, 5.5 * P.V))
