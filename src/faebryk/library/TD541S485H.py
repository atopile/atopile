# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class TD541S485H(Module):
    power: F.ElectricPower
    power_iso_in: F.ElectricPower
    power_iso_out: F.ElectricPower
    uart: F.UART_Base
    rs485: F.RS485HalfDuplex
    read_enable: F.ElectricLogic
    write_enable: F.ElectricLogic

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    @L.rt_field
    def attach_to_footprint(self):
        x = self
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": x.power.lv,
                "2": x.power.hv,
                "3": x.uart.rx.line,
                "4": x.read_enable.line,
                "5": x.write_enable.line,
                "6": x.uart.tx.line,
                "7": x.power.hv,
                "8": x.power.lv,
                "9": x.power_iso_out.lv,
                "10": x.power_iso_out.hv,
                "13": x.rs485.diff_pair.n.line,
                "14": x.rs485.diff_pair.p.line,
                "15": x.power_iso_in.hv,
                "16": x.power_iso_in.lv,
            }
        )

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://www.mornsun-power.com/public/uploads/pdf/TD(H)541S485H.pdf"
    )

    def __preinit__(self):
        # FIXME
        # self.power.decoupled.decouple()
        # self.power_iso_in.decoupled.decouple()
        # self.power_iso_out.decoupled.decouple()

        self.power_iso_in.lv.connect(self.power_iso_out.lv)
        # TODO tolerance
        self.power_iso_out.voltage.constrain_superset(5 * P.V)

        F.ElectricLogic.connect_all_module_references(
            self,
            exclude=[
                self.power,
                self.uart,
                self.read_enable,
                self.write_enable,
            ],
        )

        # TODO: ugly
        self.rs485.diff_pair.n.reference.connect(self.power_iso_out)
        self.rs485.diff_pair.p.reference.connect(self.power_iso_out)
