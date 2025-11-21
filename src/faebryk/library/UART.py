# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class UART(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    base_uart = F.UART_Base.MakeChild()
    rts = F.ElectricLogic.MakeChild()
    cts = F.ElectricLogic.MakeChild()
    dtr = F.ElectricLogic.MakeChild()
    dsr = F.ElectricLogic.MakeChild()
    dcd = F.ElectricLogic.MakeChild()
    ri = F.ElectricLogic.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    # TODO: this creates too many connections in some projects
    # _single_electric_reference = fabll.ChildField(F.has_single_electric_reference)

    # self.rts.line.add(F.has_net_name("RTS", level=F.has_net_name.Level.SUGGESTED))
    # self.cts.line.add(F.has_net_name("CTS", level=F.has_net_name.Level.SUGGESTED))
    # self.dtr.line.add(F.has_net_name("DTR", level=F.has_net_name.Level.SUGGESTED))
    # self.dsr.line.add(F.has_net_name("DSR", level=F.has_net_name.Level.SUGGESTED))
    # self.dcd.line.add(F.has_net_name("DCD", level=F.has_net_name.Level.SUGGESTED))
    # self.ri.line.add(F.has_net_name("RI", level=F.has_net_name.Level.SUGGESTED))

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
        ).put_on_type()
    )
