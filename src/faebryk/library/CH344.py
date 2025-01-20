# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.units import P
from faebryk.libs.util import not_none  # noqa: F401

logger = logging.getLogger(__name__)


class CH344(Module):
    """
    Quad UART to USB bridge
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    usb: F.USB2_0_IF.Data
    uart = L.list_field(4, F.UART)
    act: F.ElectricLogic
    indicator_tx: F.ElectricLogic
    indicator_rx: F.ElectricLogic
    osc = L.list_field(2, F.Electrical)
    reset: F.ElectricLogic
    test: F.ElectricLogic
    cfg: F.ElectricLogic
    gpio = L.list_field(16, F.ElectricLogic)
    power: F.ElectricPower

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            not_none(F.ElectricLogic.connect_all_module_references(self))
        )

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wch-ic.com/downloads/CH344DS1_PDF.html"
    )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.U
    )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------
        self.gpio[0].connect(self.uart[0].cts)
        self.gpio[1].connect(self.uart[0].rts)
        self.gpio[2].connect(self.uart[1].cts)
        self.gpio[3].connect(self.uart[1].rts)
        self.gpio[4].connect(self.uart[2].cts)
        self.gpio[5].connect(self.uart[2].rts)
        self.gpio[6].connect(self.uart[3].cts)
        self.gpio[7].connect(self.uart[3].rts)
        self.gpio[8].connect(self.uart[0].dtr)
        self.gpio[9].connect(self.uart[1].dtr)
        self.gpio[10].connect(self.uart[2].dtr)
        self.gpio[11].connect(self.uart[3].dtr)
        self.gpio[12].connect(self.uart[0].dcd)
        self.gpio[13].connect(self.uart[0].ri)
        self.gpio[14].connect(self.uart[0].dsr)
        self.gpio[15].connect(self.uart[1].dcd)

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        self.power.voltage.constrain_subset(L.Range.from_center_rel(3.3 * P.V, 0.1))
