# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P
from faebryk.libs.util import assert_once  # noqa: F401

logger = logging.getLogger(__name__)


class Analog_Devices_ADM2587EBRWZ(Module):
    """
    Signal and power isolated RS-485 full/half-duplex transceiver with
    ±15 kV ESD protection
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    power_unisolated: F.ElectricPower
    power_isolated_out: F.ElectricPower
    power_isolated_in: F.ElectricPower
    uart: F.UART_Base
    read_enable: F.ElectricLogic
    write_enable: F.ElectricLogic
    rs485: F.RS485HalfDuplex

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C12081"})
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Analog Devices",
            DescriptiveProperties.partno: "ADM2587EBRWZ-REEL7",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.lcsc.com/datasheet/lcsc_datasheet_1809121646_Analog-Devices-ADM2587EBRWZ-REEL7_C12081.pdf"  # noqa: E501
    )

    @L.rt_field
    def can_attach_to_footprint(self):
        return F.can_attach_to_footprint_via_pinmap(
            pinmap={
                "1": self.power_unisolated.lv,
                "2": self.power_unisolated.hv,
                "3": self.power_unisolated.lv,
                "4": self.uart.rx.signal,
                "5": self.read_enable.signal,
                "6": self.write_enable.signal,
                "7": self.uart.tx.signal,
                "8": self.power_unisolated.hv,
                "9": self.power_unisolated.lv,
                "10": self.power_unisolated.lv,
                "11": self.power_isolated_out.lv,
                "12": self.power_isolated_out.hv,
                "13": self.rs485.diff_pair.p.signal,
                "14": self.power_isolated_out.lv,
                "15": self.rs485.diff_pair.n.signal,
                "16": self.power_isolated_out.lv,
                "17": self.rs485.diff_pair.n.signal,
                "18": self.rs485.diff_pair.p.signal,
                "19": self.power_isolated_in.hv,
                "20": self.power_isolated_out.lv,
            }
        )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.rs485.diff_pair.p.signal: ["A"],
                self.rs485.diff_pair.n.signal: ["B"],
                self.write_enable.signal: ["DE"],
                self.power_unisolated.lv: ["GND1"],
                self.power_isolated_out.lv: ["GND2"],
                self.read_enable.signal: ["RE#"],
                self.uart.rx.signal: ["RXD"],
                self.uart.tx.signal: ["TXD"],
                self.power_unisolated.hv: ["VCC"],
                self.power_isolated_in.hv: ["VISOIN"],
                self.power_isolated_out.hv: ["VISOOUT"],
                self.rs485.diff_pair.p.signal: ["Y"],
                self.rs485.diff_pair.n.signal: ["Z"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __init__(self, full_duplex: bool = False):
        super().__init__()
        self._full_duplex = full_duplex
        if full_duplex:
            raise NotImplementedError("Full duplex RS485 not implemented")

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power_isolated_out.voltage.merge(F.Range.from_center_rel(3.3 * P.V, 0.1))
        self.power_unisolated.voltage.merge(F.Range(3.3 * P.V, 5 * P.V))

        F.ElectricLogic.connect_all_module_references(
            self,
            exclude=[
                self.power_unisolated,
                self.uart,
                self.read_enable,
                self.write_enable,
            ],
        )

        # TODO: ugly
        self.rs485.diff_pair.n.reference.connect(self.power_isolated_out)
        self.rs485.diff_pair.p.reference.connect(self.power_isolated_out)
