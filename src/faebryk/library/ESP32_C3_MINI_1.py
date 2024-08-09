# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.ESP32_C3 import ESP32_C3
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.UART_Base import UART_Base
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class ESP32_C3_MINI_1(Module):
    """ESP32-C3-MINI-1 module"""

    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()):
            esp32_c3 = ESP32_C3()
            # TODO: add components as described in the datasheet

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            rf_output = Electrical()
            chip_enable = ElectricLogic()
            gpio = times(
                22, ElectricLogic
            )  # TODO: Only GPIO 0 to 10 and 18, 19 are exposed
            uart = UART_Base()
            vdd3v3 = ElectricPower()

        self.IFs = _IFs(self)

        # TODO: connect all components (nodes)

        # connect all logic references
        ref = ElectricLogic.connect_all_module_references(self)
        self.add_trait(has_single_electric_reference_defined(ref))

        # connect power decoupling caps
        self.IFs.vdd3v3.get_trait(can_be_decoupled).decouple()

        for i, gpio in enumerate(self.IFs.gpio):
            gpio.connect(self.NODEs.esp32_c3.IFs.gpio[i])

        gnd = self.IFs.vdd3v3.IFs.lv

        self.pinmap_default = {
            "1": gnd,
            "2": gnd,
            "3": self.IFs.vdd3v3.IFs.hv,
            # 4 is not connected
            "5": self.IFs.gpio[2].IFs.signal,
            "6": self.IFs.gpio[3].IFs.signal,
            # 7 is not connected
            "8": self.IFs.chip_enable.IFs.signal,
            # 9 is not connected
            # 10 is not connected
            "11": gnd,
            "12": self.IFs.gpio[0].IFs.signal,
            "13": self.IFs.gpio[1].IFs.signal,
            "14": gnd,
            # 15 is not connected
            "16": self.IFs.gpio[10].IFs.signal,
            # 17 is not connected
            "18": self.IFs.gpio[4].IFs.signal,
            "19": self.IFs.gpio[5].IFs.signal,
            "20": self.IFs.gpio[6].IFs.signal,
            "21": self.IFs.gpio[7].IFs.signal,
            "22": self.IFs.gpio[8].IFs.signal,
            "23": self.IFs.gpio[9].IFs.signal,
            # 24 is not connected
            # 25 is not connected
            "26": self.IFs.gpio[18].IFs.signal,
            "27": self.IFs.gpio[19].IFs.signal,
            # 28 is not connected
            # 29 is not connected
            "30": self.IFs.uart.IFs.rx.IFs.signal,
            "31": self.IFs.uart.IFs.tx.IFs.signal,
            # 32 is not connected
            # 33 is not connected
            # 34 is not connected
            # 35 is not connected
            "36": gnd,
            "37": gnd,
            "38": gnd,
            "39": gnd,
            "40": gnd,
            "41": gnd,
            "42": gnd,
            "43": gnd,
            "44": gnd,
            "45": gnd,
            "46": gnd,
            "47": gnd,
            "48": gnd,
            "49": gnd,
            "50": gnd,
            "51": gnd,
            "52": gnd,
            "53": gnd,
            "54": gnd,
            "55": gnd,
            "56": gnd,
            "57": gnd,
            "58": gnd,
            "59": gnd,
            "60": gnd,
            "61": gnd,
        }
        self.pinmap = dict(self.pinmap_default)

        self.add_trait(can_attach_to_footprint_via_pinmap(self.pinmap))

        # TODO: set the following in the pinmux
        # UART0 gpio 20/21

        self.add_trait(has_designator_prefix_defined("U"))

        self.add_trait(
            has_datasheet_defined(
                "https://www.espressif.com/sites/default/files/russianDocumentation/esp32-c3-mini-1_datasheet_en.pdf"
            )
        )
