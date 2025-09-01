# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class UART(ModuleInterface):
    base_uart: F.UART_Base
    rts: F.ElectricLogic
    cts: F.ElectricLogic
    dtr: F.ElectricLogic
    dsr: F.ElectricLogic
    dcd: F.ElectricLogic
    ri: F.ElectricLogic

    # TODO: this creates too many connections in some projects
    # @L.rt_field
    # def single_electric_reference(self):
    #    return F.has_single_electric_reference_defined(
    #       F.ElectricLogic.connect_all_module_references(self)
    #   )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.rts.line.add(F.has_net_name("RTS", level=F.has_net_name.Level.SUGGESTED))
        self.cts.line.add(F.has_net_name("CTS", level=F.has_net_name.Level.SUGGESTED))
        self.dtr.line.add(F.has_net_name("DTR", level=F.has_net_name.Level.SUGGESTED))
        self.dsr.line.add(F.has_net_name("DSR", level=F.has_net_name.Level.SUGGESTED))
        self.dcd.line.add(F.has_net_name("DCD", level=F.has_net_name.Level.SUGGESTED))
        self.ri.line.add(F.has_net_name("RI", level=F.has_net_name.Level.SUGGESTED))

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import UART, ElectricPower

        uart = new UART
        uart.base_uart.baud_rate = 115200

        # Connect power reference for logic levels
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        uart.base_uart.tx.reference ~ power_3v3
        uart.base_uart.rx.reference ~ power_3v3
        uart.rts.reference ~ power_3v3
        uart.cts.reference ~ power_3v3

        # Connect to microcontroller
        microcontroller.uart ~ uart

        # Connect to external UART device or RS232 transceiver
        external_device.uart_rx ~ uart.base_uart.tx.line
        external_device.uart_tx ~ uart.base_uart.rx.line

        # Hardware flow control (optional)
        external_device.rts ~ uart.cts.line
        external_device.cts ~ uart.rts.line

        # Common baud rates: 9600, 38400, 115200, 230400, 460800
        """,
        language=F.has_usage_example.Language.ato,
    )
